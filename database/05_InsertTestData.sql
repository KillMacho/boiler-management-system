-- =============================================================================
-- 05_InsertTestData.sql
-- Тестовые (начальные) данные для BoilerManagementDB.
--
-- Состав:
--   * Справочники (типы, приоритеты, категории, роли, квалификации)
--   * 15 котельных в Москве с реальными адресами и координатами
--   * 3 склада, 50 материалов в 8 категориях, остатки
--   * 6 подразделений, 10 должностей, 20 сотрудников, контакты
--   * 5 бригад с составом, связи квалификаций с работами
--   * 5 заказчиков
--   * Пороги по 7 параметрам (общие — boiler_id = NULL)
-- =============================================================================

USE BoilerManagementDB;
GO

SET NOCOUNT ON;
BEGIN TRANSACTION;
BEGIN TRY

-- =============================================================================
-- СПРАВОЧНИКИ
-- =============================================================================

INSERT INTO equipment_categories (name, description) VALUES
    (N'Котёл',                      N'Водогрейные и паровые котлы'),
    (N'Горелка',                    N'Газовые и жидкотопливные горелки'),
    (N'Насос',                      N'Циркуляционные, сетевые, подпиточные насосы'),
    (N'Теплообменник',              N'Пластинчатые и кожухотрубные'),
    (N'КИПиА',                      N'Контрольно-измерительные приборы и автоматика'),
    (N'Запорная арматура',          N'Задвижки, клапаны, шаровые краны'),
    (N'Газовое оборудование',       N'ГРП, ГРУ, регуляторы давления'),
    (N'Дымовая труба',              N'Дымоходы, газоходы'),
    (N'Водоподготовка',             N'Фильтры, умягчители, деаэраторы'),
    (N'Электрооборудование',        N'Шкафы управления, частотные преобразователи');

INSERT INTO request_types (name) VALUES
    (N'Авария'),
    (N'Аварийное ТО'),
    (N'Плановое ТО'),
    (N'Предиктивное ТО'),
    (N'Текущий ремонт'),
    (N'Осмотр'),
    (N'Диагностика'),
    (N'Замена узлов'),
    (N'Калибровка КИПиА'),
    (N'Чистка оборудования');

INSERT INTO request_priorities (name, response_time_minutes) VALUES
    (N'Критический',    15),
    (N'Высокий',        60),
    (N'Средний',        240),
    (N'Низкий',         1440);

INSERT INTO maintenance_types (name, periodicity_days) VALUES
    (N'ТО-1 (ежемесячное)',     30),
    (N'ТО-2 (квартальное)',     90),
    (N'ТО-3 (годовое)',         365),
    (N'Текущий ремонт',         180),
    (N'Капитальный ремонт',     1825);

INSERT INTO material_categories (name) VALUES
    (N'Запчасти для насосов'),
    (N'Запчасти для горелок'),
    (N'Запорная арматура'),
    (N'КИПиА и автоматика'),
    (N'Уплотнения и прокладки'),
    (N'Электрокомпоненты'),
    (N'Химия и реагенты'),
    (N'Расходные материалы');

INSERT INTO departments (name) VALUES
    (N'Диспетчерская служба'),
    (N'Аварийная служба'),
    (N'Участок ТО и ремонта'),
    (N'Склад'),
    (N'Бухгалтерия'),
    (N'Отдел кадров');

INSERT INTO positions (name, base_salary) VALUES
    (N'Диспетчер',                  65000.00),
    (N'Главный инженер',            140000.00),
    (N'Мастер участка',             95000.00),
    (N'Бригадир',                   85000.00),
    (N'Оператор котельной',         60000.00),
    (N'Слесарь-ремонтник',          70000.00),
    (N'Электрогазосварщик',         75000.00),
    (N'Электрик',                   68000.00),
    (N'Кладовщик',                  55000.00),
    (N'Бухгалтер',                  70000.00);

INSERT INTO qualifications (name, description) VALUES
    (N'Оператор котельной',         N'Обслуживание котельных агрегатов'),
    (N'Слесарь-ремонтник',          N'Механический ремонт оборудования'),
    (N'Электрогазосварщик',         N'Сварочные работы (электро- и газосварка)'),
    (N'Электрик',                   N'Электромонтажные работы'),
    (N'Слесарь КИПиА',              N'Обслуживание приборов и автоматики'),
    (N'Газовщик',                   N'Работы с газовым оборудованием'),
    (N'Теплотехник',                N'Инженерные расчёты теплоснабжения');

INSERT INTO roles (name) VALUES
    (N'dispatcher'),
    (N'chief_engineer'),
    (N'master'),
    (N'brigade_leader'),
    (N'operator'),
    (N'storekeeper'),
    (N'accountant'),
    (N'hr_officer'),
    (N'employee');

-- =============================================================================
-- КОТЕЛЬНЫЕ (15 объектов, реальные адреса Москвы)
-- =============================================================================

INSERT INTO boilers (name, address, latitude, longitude, commissioning_date, status) VALUES
    (N'Котельная №1 "Лефортово"',       N'г. Москва, 2-я Бауманская ул., 5',         55.770000, 37.685000, '2015-09-01', N'active'),
    (N'Котельная №2 "Сокольники"',      N'г. Москва, ул. Стромынка, 18',             55.790000, 37.680000, '2012-10-15', N'active'),
    (N'Котельная №3 "Измайлово"',       N'г. Москва, Измайловский пр., 61',          55.795000, 37.769000, '2018-06-20', N'active'),
    (N'Котельная №4 "Перово"',          N'г. Москва, Зелёный пр., 66',               55.749000, 37.783000, '2010-11-10', N'active'),
    (N'Котельная №5 "Кузьминки"',       N'г. Москва, Волгоградский пр., 183',        55.696000, 37.765000, '2016-08-01', N'active'),
    (N'Котельная №6 "Марьино"',         N'г. Москва, ул. Братиславская, 26',         55.655000, 37.757000, '2019-05-15', N'active'),
    (N'Котельная №7 "Царицыно"',        N'г. Москва, ул. Весёлая, 1',                55.612000, 37.670000, '2014-03-10', N'maintenance'),
    (N'Котельная №8 "Чертаново"',       N'г. Москва, Чертановская ул., 35',          55.625000, 37.606000, '2013-09-25', N'active'),
    (N'Котельная №9 "Коньково"',        N'г. Москва, ул. Профсоюзная, 132',          55.642000, 37.516000, '2017-12-05', N'active'),
    (N'Котельная №10 "Ясенево"',        N'г. Москва, Новоясеневский пр., 34',        55.598000, 37.533000, '2011-04-18', N'active'),
    (N'Котельная №11 "Солнцево"',       N'г. Москва, Солнцевский пр., 6',            55.649000, 37.390000, '2020-07-01', N'active'),
    (N'Котельная №12 "Кунцево"',        N'г. Москва, Рублёвское ш., 42',             55.747000, 37.415000, '2009-02-20', N'active'),
    (N'Котельная №13 "Тушино"',         N'г. Москва, Волоколамское ш., 112',         55.836000, 37.420000, '2015-10-30', N'active'),
    (N'Котельная №14 "Бибирево"',       N'г. Москва, ул. Лескова, 25',               55.895000, 37.598000, '2018-11-12', N'active'),
    (N'Котельная №15 "Отрадное"',       N'г. Москва, Алтуфьевское ш., 28',           55.870000, 37.600000, '2021-06-01', N'active');

-- =============================================================================
-- СКЛАДЫ
-- =============================================================================

INSERT INTO warehouses (name, address) VALUES
    (N'Центральный склад',      N'г. Москва, ул. Складочная, 1, стр. 18'),
    (N'Склад Север',            N'г. Москва, Дмитровское ш., 157'),
    (N'Склад Юг',               N'г. Москва, Каширское ш., 61');

-- =============================================================================
-- МАТЕРИАЛЫ (50 позиций)
-- =============================================================================

-- Используем подзапросы к material_categories по имени — стабильнее, чем захардкоженные id.
DECLARE @cat_pumps INT       = (SELECT id FROM material_categories WHERE name = N'Запчасти для насосов');
DECLARE @cat_burners INT     = (SELECT id FROM material_categories WHERE name = N'Запчасти для горелок');
DECLARE @cat_valves INT      = (SELECT id FROM material_categories WHERE name = N'Запорная арматура');
DECLARE @cat_kipia INT       = (SELECT id FROM material_categories WHERE name = N'КИПиА и автоматика');
DECLARE @cat_seals INT       = (SELECT id FROM material_categories WHERE name = N'Уплотнения и прокладки');
DECLARE @cat_electro INT     = (SELECT id FROM material_categories WHERE name = N'Электрокомпоненты');
DECLARE @cat_chem INT        = (SELECT id FROM material_categories WHERE name = N'Химия и реагенты');
DECLARE @cat_cons INT        = (SELECT id FROM material_categories WHERE name = N'Расходные материалы');

INSERT INTO materials (category_id, name, unit, barcode, min_stock, price) VALUES
    -- Запчасти для насосов (7)
    (@cat_pumps,    N'Подшипник SKF 6308',                      N'шт',  N'4601234500001',   10,     1250.00),
    (@cat_pumps,    N'Торцевое уплотнение Burgmann 25мм',       N'шт',  N'4601234500002',   5,      3800.00),
    (@cat_pumps,    N'Рабочее колесо Wilo DN65',                N'шт',  N'4601234500003',   2,      18500.00),
    (@cat_pumps,    N'Вал насосный 30мм хромированный',         N'шт',  N'4601234500004',   4,      6200.00),
    (@cat_pumps,    N'Муфта упругая МУВП-90',                   N'шт',  N'4601234500005',   6,      2400.00),
    (@cat_pumps,    N'Сальник графитовый GS-10',                N'м',   N'4601234500006',   20,     320.00),
    (@cat_pumps,    N'Подшипник качения 6207',                  N'шт',  N'4601234500007',   10,     850.00),
    -- Запчасти для горелок (6)
    (@cat_burners,  N'Форсунка газовая Weishaupt WG30',         N'шт',  N'4601234500010',   3,      8400.00),
    (@cat_burners,  N'Электрод розжига L=210мм',                N'шт',  N'4601234500011',   8,      950.00),
    (@cat_burners,  N'Фотоэлемент UV Honeywell',                N'шт',  N'4601234500012',   4,      5600.00),
    (@cat_burners,  N'Вентилятор горелочный EBM 90Вт',          N'шт',  N'4601234500013',   2,      14200.00),
    (@cat_burners,  N'Сервопривод SQN31 Siemens',               N'шт',  N'4601234500014',   3,      12800.00),
    (@cat_burners,  N'Клапан газовый Dungs MVD 515',            N'шт',  N'4601234500015',   2,      19500.00),
    -- Запорная арматура (7)
    (@cat_valves,   N'Задвижка стальная 30с41нж Ду50',          N'шт',  N'4601234500020',   5,      4800.00),
    (@cat_valves,   N'Задвижка чугунная Ду100',                 N'шт',  N'4601234500021',   3,      9500.00),
    (@cat_valves,   N'Кран шаровой стальной Ду25',              N'шт',  N'4601234500022',   10,     1250.00),
    (@cat_valves,   N'Клапан обратный Ду50',                    N'шт',  N'4601234500023',   6,      2800.00),
    (@cat_valves,   N'Вентиль запорный Ду15',                   N'шт',  N'4601234500024',   15,     680.00),
    (@cat_valves,   N'Клапан предохранительный 17с28нж Ду40',   N'шт',  N'4601234500025',   3,      7200.00),
    (@cat_valves,   N'Фильтр сетчатый Ду50',                    N'шт',  N'4601234500026',   4,      3100.00),
    -- КИПиА (7)
    (@cat_kipia,    N'Датчик давления ПД-Р 0-1,6 МПа',          N'шт',  N'4601234500030',   5,      4500.00),
    (@cat_kipia,    N'Датчик температуры Pt100',                N'шт',  N'4601234500031',   8,      1800.00),
    (@cat_kipia,    N'Манометр МП-100 0-1,0 МПа',               N'шт',  N'4601234500032',   10,     850.00),
    (@cat_kipia,    N'Термометр биметаллический БТ-51',         N'шт',  N'4601234500033',   8,      650.00),
    (@cat_kipia,    N'Газоанализатор CO MRU S-Bench',           N'шт',  N'4601234500034',   1,      185000.00),
    (@cat_kipia,    N'Датчик уровня буйковый',                  N'шт',  N'4601234500035',   2,      16500.00),
    (@cat_kipia,    N'Контроллер Овен ПЛК110',                  N'шт',  N'4601234500036',   2,      28000.00),
    -- Уплотнения и прокладки (5)
    (@cat_seals,    N'Прокладка паронитовая Ду50',              N'шт',  N'4601234500040',   30,     85.00),
    (@cat_seals,    N'Прокладка фланцевая Ду100',               N'шт',  N'4601234500041',   20,     180.00),
    (@cat_seals,    N'Шнур асбестовый 8мм',                     N'м',   N'4601234500042',   50,     120.00),
    (@cat_seals,    N'Набивка сальниковая АП-31',               N'кг',  N'4601234500043',   5,      780.00),
    (@cat_seals,    N'Кольцо резиновое 25х3',                   N'шт',  N'4601234500044',   100,    15.00),
    -- Электрокомпоненты (6)
    (@cat_electro,  N'Пускатель ПМЛ-1220',                      N'шт',  N'4601234500050',   5,      1850.00),
    (@cat_electro,  N'Реле промежуточное РП-21',                N'шт',  N'4601234500051',   10,     420.00),
    (@cat_electro,  N'Автомат ВА47-29 16А',                     N'шт',  N'4601234500052',   15,     320.00),
    (@cat_electro,  N'Кабель ВВГнг 3х2,5',                      N'м',   N'4601234500053',   100,    95.00),
    (@cat_electro,  N'Частотный преобразователь Danfoss 5,5кВт',N'шт',  N'4601234500054',   1,      64000.00),
    (@cat_electro,  N'Сигнальная лампа AD22 24В',               N'шт',  N'4601234500055',   20,     85.00),
    -- Химия и реагенты (5)
    (@cat_chem,     N'Соль таблетированная "Мозырьсоль"',       N'кг',  N'4601234500060',   200,    28.00),
    (@cat_chem,     N'Гидразин-гидрат ГОСТ 19503',              N'кг',  N'4601234500061',   20,     1200.00),
    (@cat_chem,     N'Трилон Б технический',                    N'кг',  N'4601234500062',   50,     540.00),
    (@cat_chem,     N'Ингибитор коррозии ИК-Л-1',               N'кг',  N'4601234500063',   30,     980.00),
    (@cat_chem,     N'Силикатный герметик Penosil',             N'шт',  N'4601234500064',   15,     420.00),
    -- Расходные материалы (7)
    (@cat_cons,     N'ФУМ-лента 19мм',                          N'шт',  N'4601234500070',   50,     45.00),
    (@cat_cons,     N'Пакля льняная 200г',                      N'шт',  N'4601234500071',   20,     180.00),
    (@cat_cons,     N'Ветошь хлопковая',                        N'кг',  N'4601234500072',   30,     220.00),
    (@cat_cons,     N'Смазка ЛИТОЛ-24',                         N'кг',  N'4601234500073',   10,     340.00),
    (@cat_cons,     N'Электрод сварочный МР-3 3мм',             N'кг',  N'4601234500074',   20,     280.00),
    (@cat_cons,     N'Круг отрезной 125х1,6 по металлу',        N'шт',  N'4601234500075',   50,     85.00),
    (@cat_cons,     N'Перчатки рабочие х/б',                    N'пара',N'4601234500076',   100,    45.00);

-- =============================================================================
-- ОСТАТКИ НА СКЛАДАХ
-- Распределяем: ~60% позиций есть на Центральном, по ~30% на Север и Юг.
-- =============================================================================

DECLARE @wh_central INT = (SELECT id FROM warehouses WHERE name = N'Центральный склад');
DECLARE @wh_north INT   = (SELECT id FROM warehouses WHERE name = N'Склад Север');
DECLARE @wh_south INT   = (SELECT id FROM warehouses WHERE name = N'Склад Юг');

INSERT INTO material_stock (material_id, warehouse_id, quantity, reserved_quantity)
SELECT m.id, @wh_central, m.min_stock * 3, 0
FROM materials m;

-- На складе Север — половина номенклатуры (чётные id), по 1.5 нормы.
INSERT INTO material_stock (material_id, warehouse_id, quantity, reserved_quantity)
SELECT m.id, @wh_north, m.min_stock * 1.5, 0
FROM materials m WHERE m.id % 2 = 0;

-- На складе Юг — другая половина (нечётные id).
INSERT INTO material_stock (material_id, warehouse_id, quantity, reserved_quantity)
SELECT m.id, @wh_south, m.min_stock * 1.5, 0
FROM materials m WHERE m.id % 2 = 1;

-- =============================================================================
-- СОТРУДНИКИ (20 человек)
-- =============================================================================

DECLARE @dep_dispatch INT = (SELECT id FROM departments WHERE name = N'Диспетчерская служба');
DECLARE @dep_emergency INT = (SELECT id FROM departments WHERE name = N'Аварийная служба');
DECLARE @dep_maint INT = (SELECT id FROM departments WHERE name = N'Участок ТО и ремонта');
DECLARE @dep_stock INT = (SELECT id FROM departments WHERE name = N'Склад');
DECLARE @dep_acc INT = (SELECT id FROM departments WHERE name = N'Бухгалтерия');
DECLARE @dep_hr INT = (SELECT id FROM departments WHERE name = N'Отдел кадров');

DECLARE @pos_dispatch INT = (SELECT id FROM positions WHERE name = N'Диспетчер');
DECLARE @pos_chief INT = (SELECT id FROM positions WHERE name = N'Главный инженер');
DECLARE @pos_master INT = (SELECT id FROM positions WHERE name = N'Мастер участка');
DECLARE @pos_leader INT = (SELECT id FROM positions WHERE name = N'Бригадир');
DECLARE @pos_operator INT = (SELECT id FROM positions WHERE name = N'Оператор котельной');
DECLARE @pos_slesar INT = (SELECT id FROM positions WHERE name = N'Слесарь-ремонтник');
DECLARE @pos_welder INT = (SELECT id FROM positions WHERE name = N'Электрогазосварщик');
DECLARE @pos_elec INT = (SELECT id FROM positions WHERE name = N'Электрик');
DECLARE @pos_store INT = (SELECT id FROM positions WHERE name = N'Кладовщик');
DECLARE @pos_acc INT = (SELECT id FROM positions WHERE name = N'Бухгалтер');

INSERT INTO employees (first_name, last_name, middle_name, employee_number, department_id, position_id, hire_date, status) VALUES
    (N'Александр', N'Иванов',      N'Петрович',     N'EMP-0001', @dep_maint,     @pos_chief,    '2010-03-15', N'active'),
    (N'Михаил',    N'Петров',      N'Сергеевич',    N'EMP-0002', @dep_maint,     @pos_master,   '2012-06-01', N'active'),
    (N'Дмитрий',   N'Сидоров',     N'Иванович',     N'EMP-0003', @dep_maint,     @pos_master,   '2014-02-10', N'active'),
    (N'Сергей',    N'Кузнецов',    N'Владимирович', N'EMP-0004', @dep_emergency, @pos_leader,   '2015-09-20', N'active'),
    (N'Андрей',    N'Смирнов',     N'Николаевич',   N'EMP-0005', @dep_emergency, @pos_leader,   '2016-04-12', N'active'),
    (N'Павел',     N'Попов',       N'Александрович',N'EMP-0006', @dep_maint,     @pos_leader,   '2017-01-25', N'active'),
    (N'Николай',   N'Васильев',    N'Дмитриевич',   N'EMP-0007', @dep_maint,     @pos_leader,   '2018-07-08', N'active'),
    (N'Олег',      N'Новиков',     N'Викторович',   N'EMP-0008', @dep_maint,     @pos_slesar,   '2019-05-17', N'active'),
    (N'Владимир',  N'Фёдоров',     N'Юрьевич',      N'EMP-0009', @dep_emergency, @pos_slesar,   '2020-02-14', N'active'),
    (N'Евгений',   N'Морозов',     N'Александрович',N'EMP-0010', @dep_maint,     @pos_welder,   '2018-11-05', N'active'),
    (N'Илья',      N'Волков',      N'Павлович',     N'EMP-0011', @dep_maint,     @pos_welder,   '2021-03-22', N'active'),
    (N'Артём',     N'Алексеев',    N'Романович',    N'EMP-0012', @dep_maint,     @pos_elec,     '2019-08-30', N'active'),
    (N'Роман',     N'Лебедев',     N'Игоревич',     N'EMP-0013', @dep_maint,     @pos_elec,     '2020-06-18', N'active'),
    (N'Игорь',     N'Семёнов',     N'Петрович',     N'EMP-0014', @dep_dispatch,  @pos_dispatch, '2015-12-01', N'active'),
    (N'Юрий',      N'Егоров',      N'Михайлович',   N'EMP-0015', @dep_dispatch,  @pos_dispatch, '2017-06-14', N'active'),
    (N'Алексей',   N'Павлов',      N'Анатольевич',  N'EMP-0016', @dep_dispatch,  @pos_dispatch, '2022-01-10', N'active'),
    (N'Виктор',    N'Козлов',      N'Денисович',    N'EMP-0017', @dep_stock,     @pos_store,    '2016-10-03', N'active'),
    (N'Анатолий',  N'Степанов',    N'Васильевич',   N'EMP-0018', @dep_stock,     @pos_store,    '2019-04-27', N'active'),
    (N'Елена',     N'Николаева',   N'Сергеевна',    N'EMP-0019', @dep_acc,       @pos_acc,      '2013-02-18', N'active'),
    (N'Татьяна',   N'Орлова',      N'Андреевна',    N'EMP-0020', @dep_hr,        @pos_acc,      '2014-09-09', N'active');

-- =============================================================================
-- КОНТАКТЫ СОТРУДНИКОВ (email для рассылки)
-- =============================================================================

INSERT INTO employee_contacts (employee_id, email, email_verified, email_notifications_enabled)
SELECT id,
       LOWER(
           -- транслитерация упрощённая: достаточно для тестовых email
           REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
           REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
           REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
               employee_number, N'EMP-', N'emp'),
           N' ', N''), N'А',N'a'),N'Б',N'b'),N'В',N'v'),N'Г',N'g'),N'Д',N'd'),N'Е',N'e'),N'Ж',N'zh'),
           N'З',N'z'),N'И',N'i'),N'Й',N'y'),N'К',N'k'),N'Л',N'l'),N'М',N'm'),N'Н',N'n'),N'О',N'o'),
           N'П',N'p'),N'Р',N'r'),N'С',N's'),N'Т',N't'),N'У',N'u'),N'Ф',N'f'),N'Х',N'h'),N'Ц',N'c'),
           N'Ч',N'ch'),N'Ш',N'sh'),N'Щ',N'sch'),N'Ы',N'y'),N'Э',N'e'),N'Ю',N'yu'),N'Я',N'ya')
       ) + N'@ktt-service.ru' AS email,
       1 AS email_verified,
       1 AS email_notifications_enabled
FROM employees;

-- =============================================================================
-- КВАЛИФИКАЦИИ СОТРУДНИКОВ (M:N)
-- =============================================================================

DECLARE @q_operator INT = (SELECT id FROM qualifications WHERE name = N'Оператор котельной');
DECLARE @q_slesar INT = (SELECT id FROM qualifications WHERE name = N'Слесарь-ремонтник');
DECLARE @q_welder INT = (SELECT id FROM qualifications WHERE name = N'Электрогазосварщик');
DECLARE @q_elec INT = (SELECT id FROM qualifications WHERE name = N'Электрик');
DECLARE @q_kipia INT = (SELECT id FROM qualifications WHERE name = N'Слесарь КИПиА');
DECLARE @q_gas INT = (SELECT id FROM qualifications WHERE name = N'Газовщик');
DECLARE @q_heat INT = (SELECT id FROM qualifications WHERE name = N'Теплотехник');

INSERT INTO employee_qualifications (employee_id, qualification_id, grade) VALUES
    -- Главный инженер (Иванов) — теплотехник, без разряда
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0001'), @q_heat,     NULL),
    -- Мастер Петров — теплотехник + слесарь 6
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0002'), @q_heat,     NULL),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0002'), @q_slesar,   6),
    -- Мастер Сидоров — теплотехник + КИПиА 6
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0003'), @q_heat,     NULL),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0003'), @q_kipia,    6),
    -- Бригадиры-слесари
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0004'), @q_slesar,   6),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0004'), @q_gas,      5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0005'), @q_slesar,   5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0005'), @q_welder,   5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0006'), @q_slesar,   6),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0006'), @q_operator, 5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0007'), @q_kipia,    5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0007'), @q_elec,     5),
    -- Рабочие
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0008'), @q_slesar,   4),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0009'), @q_slesar,   5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0009'), @q_gas,      4),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0010'), @q_welder,   6),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0011'), @q_welder,   5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0012'), @q_elec,     5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0013'), @q_elec,     4),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0013'), @q_kipia,    4),
    -- Диспетчеры — операторы котельной
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0014'), @q_operator, 5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0015'), @q_operator, 5),
    ((SELECT id FROM employees WHERE employee_number = N'EMP-0016'), @q_operator, 4);

-- =============================================================================
-- БРИГАДЫ (5 штук)
-- =============================================================================

INSERT INTO brigades (name, leader_employee_id, status) VALUES
    (N'Бригада №1 "Аварийная"',     (SELECT id FROM employees WHERE employee_number = N'EMP-0004'), N'active'),
    (N'Бригада №2 "Аварийная"',     (SELECT id FROM employees WHERE employee_number = N'EMP-0005'), N'active'),
    (N'Бригада №3 "ТО Юг"',         (SELECT id FROM employees WHERE employee_number = N'EMP-0006'), N'active'),
    (N'Бригада №4 "ТО Север"',      (SELECT id FROM employees WHERE employee_number = N'EMP-0007'), N'active'),
    (N'Бригада №5 "КИПиА"',         (SELECT id FROM employees WHERE employee_number = N'EMP-0003'), N'active');

-- Состав бригад
INSERT INTO brigade_members (brigade_id, employee_id) VALUES
    -- Бригада №1: лидер Кузнецов + Фёдоров (слесарь) + Морозов (сварщик)
    ((SELECT id FROM brigades WHERE name = N'Бригада №1 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0004')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №1 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0009')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №1 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0010')),
    -- Бригада №2: лидер Смирнов + Волков (сварщик) + Алексеев (электрик)
    ((SELECT id FROM brigades WHERE name = N'Бригада №2 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0005')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №2 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0011')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №2 "Аварийная"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0012')),
    -- Бригада №3: лидер Попов + Новиков (слесарь)
    ((SELECT id FROM brigades WHERE name = N'Бригада №3 "ТО Юг"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0006')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №3 "ТО Юг"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0008')),
    -- Бригада №4: лидер Васильев + Лебедев (электрик)
    ((SELECT id FROM brigades WHERE name = N'Бригада №4 "ТО Север"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0007')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №4 "ТО Север"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0013')),
    -- Бригада №5 КИПиА: лидер Сидоров + Васильев (второй в КИПиА) + Лебедев
    ((SELECT id FROM brigades WHERE name = N'Бригада №5 "КИПиА"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0003')),
    ((SELECT id FROM brigades WHERE name = N'Бригада №5 "КИПиА"'),
     (SELECT id FROM employees WHERE employee_number = N'EMP-0013'));

-- =============================================================================
-- СВЯЗИ ТИПОВ РАБОТ С КВАЛИФИКАЦИЯМИ
-- Какие квалификации обязательны для выполнения каждого типа заявки.
-- =============================================================================

INSERT INTO work_type_qualifications (request_type_id, qualification_id) VALUES
    -- Авария: слесарь + газовщик
    ((SELECT id FROM request_types WHERE name = N'Авария'),              @q_slesar),
    ((SELECT id FROM request_types WHERE name = N'Авария'),              @q_gas),
    -- Аварийное ТО: слесарь + сварщик
    ((SELECT id FROM request_types WHERE name = N'Аварийное ТО'),        @q_slesar),
    ((SELECT id FROM request_types WHERE name = N'Аварийное ТО'),        @q_welder),
    -- Плановое ТО: оператор + слесарь
    ((SELECT id FROM request_types WHERE name = N'Плановое ТО'),         @q_operator),
    ((SELECT id FROM request_types WHERE name = N'Плановое ТО'),         @q_slesar),
    -- Предиктивное ТО: КИПиА + теплотехник
    ((SELECT id FROM request_types WHERE name = N'Предиктивное ТО'),     @q_kipia),
    ((SELECT id FROM request_types WHERE name = N'Предиктивное ТО'),     @q_heat),
    -- Текущий ремонт: слесарь + сварщик
    ((SELECT id FROM request_types WHERE name = N'Текущий ремонт'),      @q_slesar),
    ((SELECT id FROM request_types WHERE name = N'Текущий ремонт'),      @q_welder),
    -- Осмотр: оператор
    ((SELECT id FROM request_types WHERE name = N'Осмотр'),              @q_operator),
    -- Диагностика: КИПиА + теплотехник
    ((SELECT id FROM request_types WHERE name = N'Диагностика'),         @q_kipia),
    ((SELECT id FROM request_types WHERE name = N'Диагностика'),         @q_heat),
    -- Замена узлов: слесарь + сварщик + электрик
    ((SELECT id FROM request_types WHERE name = N'Замена узлов'),        @q_slesar),
    ((SELECT id FROM request_types WHERE name = N'Замена узлов'),        @q_welder),
    ((SELECT id FROM request_types WHERE name = N'Замена узлов'),        @q_elec),
    -- Калибровка КИПиА: слесарь КИПиА
    ((SELECT id FROM request_types WHERE name = N'Калибровка КИПиА'),    @q_kipia),
    -- Чистка: слесарь
    ((SELECT id FROM request_types WHERE name = N'Чистка оборудования'), @q_slesar);

-- =============================================================================
-- ЗАКАЗЧИКИ
-- =============================================================================

INSERT INTO customers (name, inn, contact_phone, contact_email) VALUES
    (N'ГБУ "Жилищник района Лефортово"',    N'7722012345',  N'+7 (495) 123-45-01',  N'lefortovo@zhilischnik.ru'),
    (N'ГБУ "Жилищник района Измайлово"',    N'7722023456',  N'+7 (495) 123-45-02',  N'izmailovo@zhilischnik.ru'),
    (N'ООО "ТеплоСервис"',                  N'7733112233',  N'+7 (495) 555-10-20',  N'info@teploservice.ru'),
    (N'ПАО "Мосэнерго"',                    N'7705023509',  N'+7 (495) 957-19-57',  N'contact@mosenergo.ru'),
    (N'АО "Мосгаз"',                        N'7709919109',  N'+7 (495) 660-60-00',  N'info@mos-gaz.ru');

-- =============================================================================
-- ПОРОГОВЫЕ ЗНАЧЕНИЯ (7 параметров, общие — boiler_id = NULL)
-- =============================================================================

INSERT INTO thresholds (boiler_id, parameter_name, min_warning, max_warning, min_critical, max_critical) VALUES
    (NULL, N'temperature_heat',     60.0,   95.0,   50.0,   105.0),   -- °C
    (NULL, N'pressure',             0.2,    0.55,   0.15,   0.65),    -- МПа
    (NULL, N'co_level',             NULL,   30.0,   NULL,   100.0),   -- ppm, только верхние пороги
    (NULL, N'gas_flow',             5.0,    120.0,  0.0,    140.0),   -- м³/ч
    (NULL, N'water_level',          100.0,  400.0,  50.0,   450.0),   -- мм
    (NULL, N'temperature_return',   40.0,   70.0,   30.0,   80.0),    -- °C
    (NULL, N'furnace_draft',        -40.0,  -5.0,   -50.0,  0.0);     -- Па (разрежение отрицательное)

-- =============================================================================
-- ПОЛЬЗОВАТЕЛИ (базовые учётки — пароли-заглушки, реальный хеш выставит backend)
-- =============================================================================

-- Пароль-заглушка: bcrypt-хеш строки "changeme123" — будет перевыпущен в бэкенде.
DECLARE @stub_hash NVARCHAR(255) = N'$2b$12$STUB_HASH_REPLACE_ME_ON_FIRST_LOGIN_0000000000000';

INSERT INTO users (username, password_hash, employee_id, is_active) VALUES
    (N'admin',          @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0001'), 1),
    (N'master_south',   @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0002'), 1),
    (N'master_kipia',   @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0003'), 1),
    (N'brigade1',       @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0004'), 1),
    (N'brigade2',       @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0005'), 1),
    (N'dispatcher1',    @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0014'), 1),
    (N'dispatcher2',    @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0015'), 1),
    (N'storekeeper',    @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0017'), 1),
    (N'accountant',     @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0019'), 1),
    (N'hr_manager',     @stub_hash, (SELECT id FROM employees WHERE employee_number = N'EMP-0020'), 1);

INSERT INTO user_roles (user_id, role_id) VALUES
    ((SELECT id FROM users WHERE username = N'admin'),          (SELECT id FROM roles WHERE name = N'chief_engineer')),
    ((SELECT id FROM users WHERE username = N'master_south'),   (SELECT id FROM roles WHERE name = N'master')),
    ((SELECT id FROM users WHERE username = N'master_kipia'),   (SELECT id FROM roles WHERE name = N'master')),
    ((SELECT id FROM users WHERE username = N'brigade1'),       (SELECT id FROM roles WHERE name = N'brigade_leader')),
    ((SELECT id FROM users WHERE username = N'brigade2'),       (SELECT id FROM roles WHERE name = N'brigade_leader')),
    ((SELECT id FROM users WHERE username = N'dispatcher1'),    (SELECT id FROM roles WHERE name = N'dispatcher')),
    ((SELECT id FROM users WHERE username = N'dispatcher2'),    (SELECT id FROM roles WHERE name = N'dispatcher')),
    ((SELECT id FROM users WHERE username = N'storekeeper'),    (SELECT id FROM roles WHERE name = N'storekeeper')),
    ((SELECT id FROM users WHERE username = N'accountant'),     (SELECT id FROM roles WHERE name = N'accountant')),
    ((SELECT id FROM users WHERE username = N'hr_manager'),     (SELECT id FROM roles WHERE name = N'hr_officer'));

END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    THROW;
END CATCH;

COMMIT TRANSACTION;

PRINT N'Тестовые данные вставлены.';
GO

