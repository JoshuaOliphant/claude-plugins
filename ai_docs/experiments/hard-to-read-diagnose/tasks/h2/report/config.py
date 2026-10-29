from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportConfig:
    region: str
    currency: str = "USD"
    include_refunds: bool = True
    # Display-only label; does not change the numbers.
    title: str = field(default="Sales", compare=False)
    rounding: int = field(default=2, compare=False)
