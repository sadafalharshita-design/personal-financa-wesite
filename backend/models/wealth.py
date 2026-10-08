from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


AccountType = Literal["CURRENT", "SAVINGS"]
TransactionType = Literal["INCOME", "EXPENSE"]
RecurringInterval = Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    image_url: str | None = None
    onboarded: bool


class AuthInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, min_length=2, max_length=80)


class AuthResponse(BaseModel):
    user: UserPublic


class OnboardingInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    account_name: str = Field(min_length=2, max_length=60)
    account_type: AccountType
    initial_balance: float = Field(ge=0, le=1_000_000_000)
    monthly_budget: float = Field(gt=0, le=100_000_000)
    goal_name: str | None = Field(default=None, max_length=80)
    goal_target: float | None = Field(default=None, gt=0, le=1_000_000_000)


class AccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    type: AccountType
    balance: float = Field(ge=0, le=1_000_000_000)
    is_default: bool = False


class AccountUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    type: AccountType
    is_default: bool = False


class Account(BaseModel):
    id: str
    name: str
    type: AccountType
    balance: float
    is_default: bool
    created_at: datetime


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float = Field(gt=0, le=100_000_000)
    description: str = Field(min_length=2, max_length=140)
    date: date
    category: str = Field(min_length=2, max_length=40)
    merchant: str | None = Field(default=None, max_length=80)
    account_id: str
    is_recurring: bool = False
    recurring_interval: RecurringInterval | None = None

    @field_validator("recurring_interval")
    @classmethod
    def recurring_interval_is_optional(cls, value: RecurringInterval | None) -> RecurringInterval | None:
        return value


class Transaction(TransactionCreate):
    id: str
    status: Literal["COMPLETED"] = "COMPLETED"
    created_at: datetime


class TransactionList(BaseModel):
    items: list[Transaction]
    total: int


class BulkDeleteInput(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


class BudgetUpdate(BaseModel):
    monthly_limit: float = Field(gt=0, le=100_000_000)
    alert_threshold: int = Field(default=80, ge=1, le=100)


class Budget(BaseModel):
    monthly_limit: float
    spent: float
    remaining: float
    usage_percentage: float
    alert_threshold: int
    month: str


class GoalCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    target_amount: float = Field(gt=0, le=1_000_000_000)
    current_amount: float = Field(default=0, ge=0, le=1_000_000_000)
    target_date: date | None = None
    priority: int = Field(default=2, ge=1, le=3)
    category: str = Field(default="Savings", min_length=2, max_length=40)


class GoalUpdate(GoalCreate):
    pass


class Goal(GoalCreate):
    id: str
    remaining_amount: float
    progress_percentage: float
    projected_completion: str | None
    created_at: datetime


class ContributionInput(BaseModel):
    amount: float = Field(gt=0, le=100_000_000)


class CategorySpend(BaseModel):
    category: str
    amount: float


class MonthlyFlow(BaseModel):
    month: str
    income: float
    expenses: float


class DashboardSummary(BaseModel):
    total_balance: float
    total_income: float
    total_expenses: float
    net_cash_flow: float
    budget_remaining: float
    savings_rate: float
    largest_category: str | None
    category_spend: list[CategorySpend]
    monthly_flow: list[MonthlyFlow]
    recent_transactions: list[Transaction]
    goals: list[Goal]


class ScenarioRequest(BaseModel):
    query: str = Field(min_length=8, max_length=300)
    safety_buffer: float = Field(default=20_000, ge=0, le=100_000_000)


class ScenarioInterpretation(BaseModel):
    scenario_type: Literal["MONTHLY_SAVING_CHANGE", "CATEGORY_REDUCTION", "GOAL_AFFORDABILITY"]
    monthly_change: float = 0
    direction: Literal["REDUCE_EXPENSE", "INCREASE_SAVING", "AFFORD_GOAL"]
    category: str | None = None
    target_amount: float | None = None
    target_name: str | None = None
    duration_months: int = 12


class ProjectionPoint(BaseModel):
    month: int
    baseline: float
    simulated: float


class ScenarioResult(BaseModel):
    id: str
    query: str
    scenario_type: str
    scenario_summary: str
    baseline_monthly_income: float
    baseline_monthly_expenses: float
    baseline_monthly_savings: float
    simulated_monthly_expenses: float
    simulated_monthly_savings: float
    current_balance: float
    projections: list[ProjectionPoint]
    goal_name: str | None
    baseline_goal_months: int | None
    simulated_goal_months: int | None
    goal_acceleration_months: int
    affordability_months: int | None
    ai_explanation: str
    ai_powered: bool
    assumptions: list[str]
    created_at: datetime
