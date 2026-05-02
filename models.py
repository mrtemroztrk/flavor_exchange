"""
models.py
─────────
Veri modelleri (dataclass'lar). DB satırlarından oluşturulur,
modüller arası taşınır.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    ADMIN  = "admin"
    WAITER = "waiter"


class OrderStatus(str, Enum):
    PENDING   = "pending"
    COOKING   = "cooking"
    SERVED    = "served"
    CANCELLED = "cancelled"


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    role: UserRole
    full_name: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=UserRole(row["role"]),
            full_name=row["full_name"],
        )


@dataclass
class Product:
    id: int
    name: str
    category: str
    cost: float
    base_price: float
    current_price: float
    min_margin: float = 0.20
    max_margin: float = 1.50
    stock: int = 100
    initial_stock: int = 100
    volatility: float = 0.005
    is_active: bool = True

    @property
    def p_min(self) -> float:
        """Asla altına inilemeyen fiyat: maliyet × (1 + min_margin)"""
        return self.cost * (1 + self.min_margin)

    @property
    def p_max(self) -> float:
        """Asla üstüne çıkılamayan fiyat: maliyet × (1 + max_margin)"""
        return self.cost * (1 + self.max_margin)

    @property
    def stock_ratio(self) -> float:
        """Stok doluluk oranı (0..1)"""
        if self.initial_stock <= 0:
            return 1.0
        return self.stock / self.initial_stock

    @classmethod
    def from_row(cls, row) -> "Product":
        return cls(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            cost=row["cost"],
            base_price=row["base_price"],
            current_price=row["current_price"],
            min_margin=row["min_margin"],
            max_margin=row["max_margin"],
            stock=row["stock"],
            initial_stock=row["initial_stock"],
            volatility=row["volatility"],
            is_active=bool(row["is_active"]),
        )


@dataclass
class OrderItem:
    product_id: int
    product_name: str
    quantity: int
    locked_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.locked_price


@dataclass
class Order:
    id: int
    waiter_id: Optional[int]
    table_no: Optional[int]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    items: list[OrderItem] = field(default_factory=list)
    is_simulated: bool = False

    @classmethod
    def from_row(cls, row) -> "Order":
        return cls(
            id=row["id"],
            waiter_id=row["waiter_id"],
            table_no=row["table_no"],
            status=OrderStatus(row["status"]),
            total_amount=row["total_amount"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_simulated=bool(row["is_simulated"]),
        )


@dataclass
class PriceTick:
    """Tek bir fiyat geçmişi kaydı."""
    product_id: int
    price: float
    timestamp: datetime
    is_simulated: bool = False
