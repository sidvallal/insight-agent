# Text-to-SQL Test Questions

## Project Overview

This document contains test questions for evaluating the Text-to-SQL AI Agent using the Olist Brazilian E-Commerce dataset.

The questions cover basic SQL operations, aggregations, filtering, joins, and analytical queries. They will be used to check whether the agent correctly converts natural-language questions into executable SQL queries.

---

## Level 1: Basic Queries

**Q1. Total Orders**

How many orders are present in the database?

**Q2. Unique Customers**

How many unique customers are there?

**Q3. Order Status**

What are the different order statuses available, and how many orders belong to each status?

**Q4. Average Product Price**

What is the average price of products sold in the order items table?

---

## Level 2: Intermediate Queries

**Q5. Top Product Categories**

What are the top 5 product categories by total sales?

**Q6. Customers by State**

Which 10 Brazilian states have the highest number of customers?

**Q7. Monthly Order Trends**

How many orders were placed in each month?

**Q8. Payment Methods**

Which payment methods are used most frequently, and how many payment records does each method have?

---

## Level 3: Advanced Queries

**Q9. Top Sellers**

Who are the top 5 sellers based on total revenue from sold items?

**Q10. Average Review Score by Category**

What is the average customer review score for each product category?

---

## Evaluation Criteria

Each question can be evaluated using the following criteria:

- **SQL correctness:** Does the generated SQL use valid syntax and the correct columns?
- **Query execution:** Does the query execute successfully against PostgreSQL?
- **Result accuracy:** Does the output correctly answer the question?
- **Join correctness:** Are table relationships handled correctly without unintended duplicate rows?
- **Response clarity:** Does the agent present the results in a clear and understandable format?

## Notes

- Use the original database table and column names.
- Use English product category names where appropriate.
- For revenue calculations, clearly distinguish product price from freight and payment amounts.
- For monthly trends, use the order purchase timestamp.
- Validate generated results against manually written SQL queries during testing.

