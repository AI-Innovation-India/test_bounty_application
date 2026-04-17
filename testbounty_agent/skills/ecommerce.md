# Skill: E-Commerce Testing

## Domain
Online retail, marketplaces, shopping platforms, B2C stores

## Trigger Keywords
shop, cart, checkout, product, catalog, order, payment, shipping, wishlist, inventory, sku, basket, purchase, buy, price, discount, coupon, promo

## Critical Test Areas

### Product Catalog
- Product listing loads with correct images, titles, prices
- Filters (category, price range, brand, rating) work correctly
- Sorting (price asc/desc, popularity, newest) works
- Search returns relevant results; empty search shows all
- Out-of-stock products are clearly marked and cannot be added to cart
- Product detail page shows correct specs, images, price

### Shopping Cart
- Add to cart from listing and detail page
- Quantity update (increase, decrease, remove)
- Cart persists across page refresh and login
- Cart shows correct subtotal, tax, shipping estimate
- Cart is cleared after successful order
- Adding same item twice increments quantity (doesn't duplicate)
- Cart badge count is accurate

### Checkout Flow (Most Critical)
- Guest checkout and logged-in checkout work
- Address form validates correctly (required fields, postal code format)
- Multiple shipping options available and selectable
- Payment form validates card number, expiry, CVV
- Order summary shows correct totals before confirmation
- Order confirmation page shows order ID and summary
- Confirmation email is triggered (if testable)

### Payment Edge Cases
- Declined card shows clear error (not generic)
- 3D Secure / OTP flow completes correctly
- Payment timeout handled gracefully
- Double-click on "Place Order" does NOT create duplicate order
- Free orders (100% discount) work without payment info

### User Account
- Order history shows past orders with correct status
- Order detail shows items, tracking info, status
- Address book save/edit/delete
- Wishlist add/remove/move to cart
- Account details update (name, email, password)

### Business Rules to Test
- Discount codes apply correctly and only once
- Bundle pricing works correctly
- Tax calculation varies by location
- Free shipping threshold applies correctly
- Stock reservation during checkout (item reserved on cart add, released on abandon)
- Flash sale pricing reverts after expiry

### Security Tests
- Price manipulation: POST to cart/checkout with modified price should fail
- Coupon stacking: multiple coupons should respect business rules
- Quantity limits enforced server-side
- Payment details never stored in browser history

## Common Selector Patterns
- Add to cart: `.add-to-cart`, `button:has-text('Add to Cart')`, `[data-action='add-to-cart']`
- Cart count: `.cart-count`, `.cart-badge`, `[aria-label*='cart']`
- Checkout button: `.checkout-btn`, `button:has-text('Checkout')`, `a:has-text('Proceed')`
- Price: `.price`, `.product-price`, `[itemprop='price']`
- Quantity: `input[name='quantity']`, `.qty-input`
