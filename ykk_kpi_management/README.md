# YKK - KPI Management

## Overview

`ykk_kpi_management` is an Odoo 18 module for managing KPI master data, KPI templates, annual KPI setup, and department evaluation records.

The module adds a main application menu named **KPI Management** with three main sections:

- **Evaluate**
- **Allocation**
- **Configuration**

It depends on the standard Odoo modules `base`, `hr`, and `mail`.

## Main Menus

### Evaluate

The **Evaluate** menu contains operational KPI evaluation documents.

#### Annual KPI

Model: `ykk.kpi.annual.kpi`

Annual KPI stores KPI indicators for an employee and period. It includes employee context and separated KPI lines by evaluation category.

Header fields:

- `Name`
- `Employee`
- `Group Job`
- `Level`
- `Department`
- `Period`
- `Responsible`
- `Date`
- `Company`

Tabs and line models:

- **Performance Evaluation**
  - Field: `performance_line_ids`
  - Model: `ykk.kpi.annual.kpi.performance.line`
- **Role-based Behavior Evaluation**
  - Field: `role_line_ids`
  - Model: `ykk.kpi.annual.kpi.role.line`
- **Behavior Evaluation**
  - Field: `behavior_line_ids`
  - Model: `ykk.kpi.annual.kpi.behavior.line`
- **Attitude Evaluation**
  - Field: `attitude_line_ids`
  - Model: `ykk.kpi.annual.kpi.attitude.line`
- **Other Info**
  - Stores indicator weights for the four evaluation categories.

Line fields:

- `Goal`
- `Achievement Criteria`
- `Weight`

Each tab filters `Goal` records by the related Goal type.

#### Department Evaluate

Model: `ykk.kpi.department.evaluate`

Department Evaluate records employee performance evaluation results for a selected period.

Header fields:

- `Name`
- `Employee`
- `Group Job`
- `Level`
- `Department`
- `Period`
- `Responsible`
- `Date`
- `Company`

Tab:

- **Performance Evaluation**

Line model: `ykk.kpi.department.evaluate.line`

Line fields:

- `Goal`
- `Achievement Criteria`
- `Weight`
- `Performance Results (Employee)`
- `Comments (First Evaluator)`
- `Score (First Evaluator)`
- `Score (Second Evaluator)`
- `Total`

Department Evaluate uses the sequence code `ykk.kpi.department.evaluate` with prefix `DE/%(year)s/%(month)s/`.

#### Department KPI

Model: `ykk.kpi.department.kpi`

Department KPI records the detailed KPI evaluation for an employee and period. It includes the four evaluation categories, calculated scores, workflow status, and a summary of related Parent KPI grades.

Header fields:

- `Name`
- `Status`: Draft, Inprocess, Evaluated, or Cancel
- `Employee`
- `Group Job`
- `Job Level`
- `Department`
- `Period`
- `Annual KPI`
- `Responsible`
- `Date`
- `Company`

Workflow:

- `Confirm` changes Draft to Inprocess.
- `Done` changes Inprocess to Evaluated.
- `Cancel` changes Draft or Inprocess to Cancel.

Tabs:

- **Performance Evaluation**: `ykk.kpi.department.kpi.performance.line`
- **Role-based Behavior Evaluation**: `ykk.kpi.department.kpi.role.line`
- **Behavior Evaluation**: `ykk.kpi.department.kpi.behavior.line`
- **Attitude Evaluation**: `ykk.kpi.department.kpi.attitude.line`
- **Summary**

Every evaluation line includes `Weight`, evaluator scores, and `Total`. `Total` is calculated as:

```text
Second Evaluator Score * Weight / 100
```

`first_evaluator_score`, `second_evaluator_score`, and `total_score` use the `KPI Score` decimal precision master data with two decimal places.

Summary fields:

- `Period Grade`: averages the totals of tabs that contain lines, truncates decimals with `int()`, then finds a Grade by matching `ykk.kpi.grade.code`.
- `Parent KPIs`: persistent summary lines using `ykk.kpi.department.kpi.summary.line`.
- `Overall Grade`: averages the numeric grade codes from the current Period Grade and all selected Parent KPI Grades, truncates decimals with `int()`, then finds the matching Grade.

Each Parent KPI can be added only once per Department KPI summary.

### Allocation

The **Allocation** menu is reserved for future KPI allocation functionality.

### Configuration

The **Configuration** menu contains KPI master data and links to standard HR setup screens.

#### KPI Template

Model: `ykk.kpi.template`

KPI Template defines reusable KPI evaluation criteria by job level and department.

Header fields:

- `Name`
- `Level`
- `Department`
- `Remark`
- `Status`: Draft, Done, or Cancel
- `Responsible`
- `Date`
- `Company`

Tab:

- **Performance Evaluation**

Line model: `ykk.kpi.template.performance.line`

Line fields:

- `Goal`
- `Achievement Criteria`
- `Weight`

Tab:

- **Employees**

Employee line model: `ykk.kpi.template.employee.line`

The Employee selector is filtered by the Department and Job Level selected on the KPI Template header. An employee can be added only once per template.

#### Goals

Model: `ykk.kpi.Goal`

Goals define KPI targets or indicators used by templates and evaluations.

Fields:

- `Code`
- `Name`
- `Type`
- `Department`
- `Company`
- `Active`

Goal type options:

- `Performance Evaluation`
- `Role-based Behavior Evaluation`
- `Behavior Evaluation`
- `Attitude Evaluation`

Constraints:

- `Code` must be unique per company.
- `Name` must be unique per company.

#### Grades

Model: `ykk.kpi.grade`

Grades define score ranges and descriptions.

Fields:

- `Name`
- `Start Score`
- `End Score`
- `Description`
- `Company`
- `Active`

Validation:

- `Start Score` must be less than or equal to `End Score`.
- `Name` must be unique per company.

#### Group Positions

Model: `ykk.kpi.group.position`

Group Positions define group job categories.

Fields:

- `Name`
- `Company`
- `Active`

Constraint:

- `Name` must be unique per company.

#### Levels

Model: `ykk.kpi.level`

Levels define employee/job levels used by KPI templates and evaluation documents.

Fields:

- `Name`
- `Description`
- `Company`
- `Active`

Constraint:

- `Name` must be unique per company.

#### Periods

Model: `ykk.kpi.period`

Periods define KPI evaluation periods.

Fields:

- `Name`
- `Period Type`
- `Start Date`
- `End Date`
- `Company`
- `Active`

Period type options:

- `Month`
- `Quarter`
- `Half Year`
- `Year`

Validation:

- `Start Date` must be less than or equal to `End Date`.
- `Name` must be unique per company.

#### Standard HR Menus

The module adds shortcuts under **Configuration** to standard Odoo HR screens:

- **Employees** opens `hr.employee`.
- **Departments** opens `hr.department`.
- **Job Positions** opens `hr.job`.

These menus reuse standard Odoo actions and views; the module does not create custom screens for them.

## Security

The module defines a security category named **KPI** and two groups:

- **KPI / User**
- **KPI / Administrator**

`KPI / Administrator` implies `KPI / User`.

Access pattern:

- Users generally have read-only access.
- Administrators have full create, read, write, and delete access.

Root and Administrator users are assigned to the administrator group by default.

## Technical Files

Important module files:

- `__manifest__.py`
- `models/kpi_goal.py`
- `models/kpi_grade.py`
- `models/kpi_group_position.py`
- `models/kpi_level.py`
- `models/kpi_period.py`
- `models/kpi_template.py`
- `models/annual_kpi.py`
- `models/department_evaluate.py`
- `models/department_kpi.py`
- `data/decimal_precision_data.xml`
- `security/security_groups.xml`
- `security/ir.model.access.csv`
- `views/menus.xml`
- `views/hr_views.xml`
- `views/kpi_*_views.xml`
- `views/annual_kpi_views.xml`
- `views/department_evaluate_views.xml`
- `views/department_kpi_views.xml`

## Installation / Upgrade

1. Place the module in an Odoo addons path.
2. Update the Apps list.
3. Install or upgrade **YKK - KPI Management**.
4. Assign users to either **KPI / User** or **KPI / Administrator**.

After upgrading, verify the following menus:

- `KPI Management > Evaluate > Annual KPI`
- `KPI Management > Evaluate > Department Evaluate`
- `KPI Management > Evaluate > Department KPI`
- `KPI Management > Configuration > KPI Template`
- `KPI Management > Configuration > Goals`
- `KPI Management > Configuration > Grades`
- `KPI Management > Configuration > Group Positions`
- `KPI Management > Configuration > Levels`
- `KPI Management > Configuration > Periods`
- `KPI Management > Configuration > Employees`
- `KPI Management > Configuration > Departments`
- `KPI Management > Configuration > Job Positions`
