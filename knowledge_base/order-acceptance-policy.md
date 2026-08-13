# Purchase order acceptance policy

An order may be automatically drafted only when the customer, every product, delivery address,
payment terms, currency, prices, totals, and purchase-order number all pass validation. A semantic
match is supporting evidence, not authority; customer and product identifiers must exist and be
active in the operational database.

Prices must match the active customer contract in the order currency within the configured
tolerance. Delivery is allowed only to a customer-approved ship-to location. A duplicate PO number
for the same customer must be sent to review. Missing, ambiguous, or low-confidence fields must be
reviewed by a human.
