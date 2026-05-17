-- Day 16: seed employee_contacts with Mailtrap test addresses
-- All emails point to the Mailtrap sandbox — no real emails are sent.
USE BoilerManagementDB;
GO

-- Insert contacts only for employees that don't already have one
INSERT INTO employee_contacts (employee_id, email, email_verified, email_notifications_enabled, last_updated)
SELECT
    e.id,
    LOWER(
        -- firstname.lastname@boiler-test.local  (Mailtrap catches everything)
        REPLACE(e.first_name, N' ', N'') + N'.' +
        REPLACE(e.last_name,  N' ', N'') + N'@boiler-test.local'
    ),
    1,   -- verified
    1,   -- notifications enabled
    SYSUTCDATETIME()
FROM employees e
WHERE e.status = N'active'
  AND NOT EXISTS (
      SELECT 1 FROM employee_contacts ec WHERE ec.employee_id = e.id
  );

PRINT 'Employee contacts seeded: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' rows';
GO
