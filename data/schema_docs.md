# Database Schema Documentation

## Overview

This document describes the PostgreSQL database used in the **AI-Powered Text-to-SQL Analytics Agent** project.

The database contains e-commerce data from the Olist Brazilian E-Commerce dataset. It consists of nine tables covering customers, orders, products, sellers, payments, reviews, and geographical information.

This documentation provides table descriptions, column definitions, primary keys, and relationships to help the AI agent generate accurate SQL queries.

---

## 1. Customers — `olist_customers_dataset`

**Purpose:** Stores customer information and location details.

| Column | Description |
|---|---|
| `customer_id` | Unique identifier for a customer record associated with an order. |
| `customer_unique_id` | Unique identifier representing a customer across multiple orders. |
| `customer_zip_code_prefix` | First five digits of the customer's ZIP code. |
| `customer_city` | Customer's city. |
| `customer_state` | Customer's Brazilian state. |

**Primary Key:** `customer_id`

**Relationships:**
- `customer_id` connects to `olist_orders_dataset.customer_id`.
- `customer_zip_code_prefix` can connect to `olist_geolocation_dataset.geolocation_zip_code_prefix`.

---

## 2. Geolocation — `olist_geolocation_dataset`

**Purpose:** Provides geographical information, including coordinates and locations associated with ZIP code prefixes.

| Column | Description |
|---|---|
| `geolocation_zip_code_prefix` | First five digits of a ZIP code. |
| `geolocation_lat` | Latitude coordinate. |
| `geolocation_lng` | Longitude coordinate. |
| `geolocation_city` | City associated with the location. |
| `geolocation_state` | Brazilian state associated with the location. |

**Primary Key:** None

**Relationships:**
- `geolocation_zip_code_prefix` can connect to customer ZIP code prefixes.
- `geolocation_zip_code_prefix` can connect to seller ZIP code prefixes.

**Important:** A ZIP code prefix can have multiple geolocation records. Direct joins may duplicate rows and inflate aggregate results.

---

## 3. Order Items — `olist_order_items_dataset`

**Purpose:** Stores product-level details for each order, including prices, shipping costs, and seller information.

| Column | Description |
|---|---|
| `order_id` | Identifier of the order containing the item. |
| `order_item_id` | Sequential item number within an order. |
| `product_id` | Identifier of the purchased product. |
| `seller_id` | Identifier of the seller providing the product. |
| `shipping_limit_date` | Deadline for the seller to hand the item over for shipping. |
| `price` | Price of the individual product. |
| `freight_value` | Shipping cost associated with the individual item. |

**Primary Key:** (`order_id`, `order_item_id`)

**Relationships:**
- `order_id` connects to `olist_orders_dataset.order_id`.
- `product_id` connects to `olist_products_dataset.product_id`.
- `seller_id` connects to `olist_sellers_dataset.seller_id`.

**Common analytical use cases:**
- Product sales analysis.
- Seller revenue analysis.
- Freight cost analysis.
- Order item counts.

---

## 4. Order Payments — `olist_order_payments_dataset`

**Purpose:** Contains payment information for orders, including payment methods, installments, and amounts.

| Column | Description |
|---|---|
| `order_id` | Identifier of the associated order. |
| `payment_sequential` | Sequential number of a payment record within an order. |
| `payment_type` | Payment method, such as credit card, boleto, voucher, or debit card. |
| `payment_installments` | Number of payment installments. |
| `payment_value` | Monetary value of the payment record. |

**Primary Key:** (`order_id`, `payment_sequential`)

**Relationships:**
- `order_id` connects to `olist_orders_dataset.order_id`.

**Common analytical use cases:**
- Revenue and payment analysis.
- Payment method popularity.
- Installment analysis.

**Important:** An order may have multiple payment records. Aggregate payment amounts by order before joining them with order items to avoid multiplying totals.

---

## 5. Order Reviews — `olist_order_reviews_dataset`

**Purpose:** Stores customer ratings and written feedback related to orders.

| Column | Description |
|---|---|
| `review_id` | Identifier of the review. |
| `order_id` | Identifier of the reviewed order. |
| `review_score` | Customer rating from 1 to 5. |
| `review_comment_title` | Short title of the customer's review. |
| `review_comment_message` | Written feedback submitted by the customer. |
| `review_creation_date` | Date when the review was created. |
| `review_answer_timestamp` | Timestamp when the review received an answer. |

**Primary Key:** (`review_id`, `order_id`)

**Relationships:**
- `order_id` connects to `olist_orders_dataset.order_id`.

**Common analytical use cases:**
- Average review score.
- Customer satisfaction analysis.
- Review score distribution.
- Review trends over time.

**Important:** Review comments are optional and may contain NULL values.

---

## 6. Orders — `olist_orders_dataset`

**Purpose:** Stores order-level information, including order status and important timestamps.

| Column | Description |
|---|---|
| `order_id` | Unique identifier for an order. |
| `customer_id` | Identifier of the customer who placed the order. |
| `order_status` | Current or final status of the order. |
| `order_purchase_timestamp` | Date and time when the order was placed. |
| `order_approved_at` | Date and time when the order was approved. |
| `order_delivered_carrier_date` | Date and time when the order was handed over to the carrier. |
| `order_delivered_customer_date` | Date and time when the order was delivered to the customer. |
| `order_estimated_delivery_date` | Estimated delivery date. |

**Primary Key:** `order_id`

**Relationships:**
- `customer_id` connects to `olist_customers_dataset.customer_id`.
- `order_id` connects to order items, payments, and reviews.

**Common analytical use cases:**
- Total order counts.
- Order status analysis.
- Monthly order trends.
- Delivery time analysis.

---

## 7. Products — `olist_products_dataset`

**Purpose:** Stores product information, including categories, descriptions, dimensions, and weight.

| Column | Description |
|---|---|
| `product_id` | Unique identifier for a product. |
| `product_category_name` | Product category name in Portuguese. |
| `product_name_lenght` | Length of the product name, as recorded in the dataset. |
| `product_description_lenght` | Length of the product description, as recorded in the dataset. |
| `product_photos_qty` | Number of product photos. |
| `product_weight_g` | Product weight in grams. |
| `product_length_cm` | Product length in centimeters. |
| `product_height_cm` | Product height in centimeters. |
| `product_width_cm` | Product width in centimeters. |

**Primary Key:** `product_id`

**Relationships:**
- `product_id` connects to `olist_order_items_dataset.product_id`.
- `product_category_name` connects to `product_category_name_translation.product_category_name`.

**Common analytical use cases:**
- Product category sales.
- Product popularity.
- Product attribute analysis.

**Important:** The original dataset uses the spellings `product_name_lenght` and `product_description_lenght`. These column names must be used exactly in SQL queries.

---

## 8. Sellers — `olist_sellers_dataset`

**Purpose:** Stores seller identifiers and location information.

| Column | Description |
|---|---|
| `seller_id` | Unique identifier for a seller. |
| `seller_zip_code_prefix` | First five digits of the seller's ZIP code. |
| `seller_city` | Seller's city. |
| `seller_state` | Seller's Brazilian state. |

**Primary Key:** `seller_id`

**Relationships:**
- `seller_id` connects to `olist_order_items_dataset.seller_id`.
- `seller_zip_code_prefix` can connect to `olist_geolocation_dataset.geolocation_zip_code_prefix`.

**Common analytical use cases:**
- Seller revenue analysis.
- Seller performance comparisons.
- Geographic seller distribution.

---

## 9. Product Category Translation — `product_category_name_translation`

**Purpose:** Maps Portuguese product category names to English translations.

| Column | Description |
|---|---|
| `product_category_name` | Original category name in Portuguese. |
| `product_category_name_english` | English translation of the category name. |

**Primary Key:** `product_category_name`

**Relationships:**
- `product_category_name` connects to `olist_products_dataset.product_category_name`.

**Common analytical use cases:**
- English-language category reporting.
- Product category comparisons.
- Sales analysis by translated category.

---

## Table Relationships Summary

| Main Table | Related Table | Join Condition |
|---|---|---|
| Customers | Orders | `customers.customer_id = orders.customer_id` |
| Orders | Order Items | `orders.order_id = order_items.order_id` |
| Products | Order Items | `products.product_id = order_items.product_id` |
| Sellers | Order Items | `sellers.seller_id = order_items.seller_id` |
| Orders | Payments | `orders.order_id = payments.order_id` |
| Orders | Reviews | `orders.order_id = reviews.order_id` |
| Products | Category Translation | `products.product_category_name = translation.product_category_name` |
| Customers | Geolocation | `customers.customer_zip_code_prefix = geolocation.geolocation_zip_code_prefix` |
| Sellers | Geolocation | `sellers.seller_zip_code_prefix = geolocation.geolocation_zip_code_prefix` |

These are logical relationships used for querying. They are not all enforced as foreign key constraints in PostgreSQL.

---

## SQL Query Guidelines for the AI Agent

- Use exact table and column names from this documentation.
- Use appropriate JOIN conditions when combining related tables.
- Use `COUNT(DISTINCT ...)` when necessary to avoid counting the same entity multiple times.
- Aggregate order items and payments separately before joining them when calculating order-level totals.
- Avoid direct aggregation after joining payments with order items, because both tables can contain multiple records per order.
- Use the English category translation table when English category names are required.
- Avoid direct geolocation joins when a single row per ZIP code is needed.
- Use the appropriate timestamp column for time-based analysis.
- Treat optional review comments and missing delivery timestamps carefully.

## Purpose in the Text-to-SQL Agent

This documentation acts as schema context for the AI agent. It helps the model:

- Understand the meaning of database tables and columns.
- Identify relationships between tables.
- Select appropriate tables for natural-language questions.
- Generate SQL queries using valid column names.
- Avoid common join and aggregation mistakes.

The schema documentation will be used alongside database metadata and the user's natural-language question during SQL generation.