"""Simulator entry point: runs 15 boilers concurrently, injects random alarms."""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import signal
import sys
from typing import Optional

from .boiler_simulator import BoilerSimulator
from .config import settings
from .scenarios import get_scenario, random_scenario
from .telemetry_sender import TelemetrySender

logger = logging.getLogger("simulator.main")


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


class SimulatorRunner:
    def __init__(
        self,
        num_boilers: int,
        interval: float,
        enable_alarms: bool,
        alarm_min: float,
        alarm_max: float,
        duration: Optional[float],
    ) -> None:
        self._num_boilers = num_boilers
        self._interval = interval
        self._enable_alarms = enable_alarms
        self._alarm_min = alarm_min
        self._alarm_max = alarm_max
        self._duration = duration
        self._stop_event = asyncio.Event()
        self._boilers = [BoilerSimulator(i + 1) for i in range(num_boilers)]

    def request_stop(self) -> None:
        self._stop_event.set()

    async def _reading_loop(self, boiler: BoilerSimulator, sender: TelemetrySender) -> None:
        """Continuously send readings for one boiler until stop is requested."""
        while not self._stop_event.is_set():
            try:
                reading = boiler.generate_reading()
                result = await sender.send(reading)
                status = result.get("status", "?")
                auto_req = result.get("auto_request_id")
                if auto_req:
                    logger.warning(
                        "boiler_id=%d  status=%s  AUTO-REQUEST #%d created",
                        boiler.boiler_id,
                        status,
                        auto_req,
                    )
                else:
                    logger.debug(
                        "boiler_id=%d  status=%s",
                        boiler.boiler_id,
                        status,
                    )
            except Exception as exc:
                logger.error("boiler_id=%d send failed: %s", boiler.boiler_id, exc)

            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stop_event.wait()),
                    timeout=self._interval,
                )
            except asyncio.TimeoutError:
                pass

    async def _alarm_scheduler(self, boiler: BoilerSimulator) -> None:
        """Randomly triggers and clears alarms for one boiler."""
        while not self._stop_event.is_set():
            wait = random.uniform(self._alarm_min, self._alarm_max)
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stop_event.wait()),
                    timeout=wait,
                )
            except asyncio.TimeoutError:
                pass

            if self._stop_event.is_set():
                break

            name, overrides = random_scenario()
            boiler.trigger_alarm(name, overrides)

            # Alarm lasts 2–5 intervals so at least one reading goes through
            alarm_duration = random.uniform(self._interval * 2, self._interval * 5)
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stop_event.wait()),
                    timeout=alarm_duration,
                )
            except asyncio.TimeoutError:
                pass

            boiler.reset_to_normal()

    async def _duration_watchdog(self) -> None:
        if self._duration is None:
            return
        try:
            await asyncio.wait_for(
                asyncio.shield(self._stop_event.wait()),
                timeout=self._duration,
            )
        except asyncio.TimeoutError:
            logger.info("Duration %ds elapsed — stopping.", int(self._duration))
            self._stop_event.set()

    async def run(self) -> None:
        async with TelemetrySender() as sender:
            tasks: list[asyncio.Task] = []

            if self._duration is not None:
                tasks.append(asyncio.create_task(self._duration_watchdog()))

            for boiler in self._boilers:
                tasks.append(asyncio.create_task(self._reading_loop(boiler, sender)))
                if self._enable_alarms:
                    tasks.append(asyncio.create_task(self._alarm_scheduler(boiler)))

            total = self._num_boilers
            alarms_str = "enabled" if self._enable_alarms else "disabled"
            logger.info(
                "Simulator started: %d boilers, interval=%.0fs, alarms=%s",
                total, self._interval, alarms_str,
            )

            await self._stop_event.wait()

            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Simulator stopped.")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Boiler telemetry simulator")
    p.add_argument("--boilers", type=int, default=settings.num_boilers,
                   help="Number of boilers to simulate (default: %(default)s)")
    p.add_argument("--interval", type=float, default=settings.send_interval,
                   help="Seconds between readings per boiler (default: %(default)s)")
    p.add_argument("--no-alarms", action="store_true",
                   help="Disable random alarm injection")
    p.add_argument("--trigger-alarm", metavar="BOILER_ID:SCENARIO",
                   help="Immediately trigger an alarm on startup, e.g. --trigger-alarm 3:overheat")
    p.add_argument("--duration", type=float, default=None,
                   help="Stop automatically after N seconds (default: run forever)")
    p.add_argument("--log-level", default=settings.log_level,
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Logging verbosity (default: %(default)s)")
    return p.parse_args()


async def _async_main() -> None:
    args = _parse_args()
    _setup_logging(args.log_level)

    runner = SimulatorRunner(
        num_boilers=args.boilers,
        interval=args.interval,
        enable_alarms=not args.no_alarms,
        alarm_min=settings.alarm_min_interval,
        alarm_max=settings.alarm_max_interval,
        duration=args.duration,
    )

    # Immediate alarm injection for manual testing
    if args.trigger_alarm:
        try:
            boiler_str, scenario_name = args.trigger_alarm.split(":", 1)
            boiler_idx = int(boiler_str) - 1
            overrides = get_scenario(scenario_name)
            runner._boilers[boiler_idx].trigger_alarm(scenario_name, overrides)
            logger.info("Pre-triggered alarm '%s' on boiler_id=%s", scenario_name, boiler_str)
        except (ValueError, IndexError, KeyError) as exc:
            logger.error("--trigger-alarm error: %s", exc)
            sys.exit(1)

    loop = asyncio.get_event_loop()

    def _on_signal() -> None:
        logger.info("Shutdown signal received.")
        runner.request_stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except (NotImplementedError, AttributeError):
            # Windows doesn't support add_signal_handler for SIGTERM
            pass

    await runner.run()


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
