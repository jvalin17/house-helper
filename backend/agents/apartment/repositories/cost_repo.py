"""Repository for apartment cost breakdowns — user-editable per listing.

Stores rent + parking + pet fee + utilities + deposit = monthly and move-in totals.
"""

import sqlite3


class CostRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection

    def get_cost(self, listing_id: int) -> dict | None:
        """Get cost breakdown for a listing."""
        row = self._connection.execute(
            "SELECT * FROM apartment_cost WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def save_cost(self, listing_id: int, **fields) -> int:
        """Save or update cost breakdown. Calculates totals automatically."""
        base_rent = fields.get("base_rent") or 0
        parking_fee = fields.get("parking_fee") or 0
        pet_fee = fields.get("pet_fee") or 0
        utilities_estimate = fields.get("utilities_estimate") or 0
        lease_months = fields.get("lease_months") or 12
        special_discount = fields.get("special_discount") or 0
        special_description = fields.get("special_description") or ""

        # Calculate effective monthly rent (with concessions)
        if special_discount and lease_months:
            total_lease_cost = (base_rent * lease_months) - special_discount
            effective_monthly = round(total_lease_cost / lease_months, 2)
        else:
            effective_monthly = base_rent

        total_monthly = round(effective_monthly + parking_fee + pet_fee + utilities_estimate, 2)

        cursor = self._connection.execute(
            """INSERT INTO apartment_cost
               (listing_id, base_rent, lease_months, special_description, special_discount,
                effective_monthly, parking_fee, pet_fee, utilities_estimate, total_monthly)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(listing_id) DO UPDATE SET
                 base_rent = excluded.base_rent,
                 lease_months = excluded.lease_months,
                 special_description = excluded.special_description,
                 special_discount = excluded.special_discount,
                 effective_monthly = excluded.effective_monthly,
                 parking_fee = excluded.parking_fee,
                 pet_fee = excluded.pet_fee,
                 utilities_estimate = excluded.utilities_estimate,
                 total_monthly = excluded.total_monthly""",
            (listing_id, base_rent, lease_months, special_description, special_discount,
             effective_monthly, parking_fee, pet_fee, utilities_estimate, total_monthly),
        )
        self._connection.commit()
        return cursor.lastrowid
