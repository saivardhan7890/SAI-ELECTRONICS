# SAI ELECTRONICS
## AWS E-Commerce Platform with Serverless APIs and Cost-Aware Audit Analytics

**Project URL:** https://saivardhan.online  
**AWS Region:** US East (N. Virginia), `us-east-1`  
**Repository:** https://github.com/saivardhan7890/SAI-ELECTRONICS

---

## 1. Project overview

SAI ELECTRONICS is a full-stack electronics e-commerce application deployed on Amazon Web Services (AWS). Customers can browse an electronics catalogue, register and log in, add products to a cart, create orders, review their order history and submit a UPI transaction reference for manual payment verification.

The platform uses an EC2-hosted web frontend and a serverless API backend. Product, customer and order data is stored in Amazon Aurora MySQL. CloudWatch provides application execution logs, while CloudTrail and Athena provide account-activity audit and SQL analytics.

## 2. Application capabilities

- Public HTTPS storefront at `https://saivardhan.online`.
- Electronics catalogue with 50 product records, product photographs, categories, prices and stock quantities.
- Customer registration and login.
- Shopping cart and order creation.
- Server-side product and stock checks during order creation.
- Customer order-history view.
- UPI QR payment instructions and transaction-reference submission.
- Admin endpoint for reviewing pending payment references.

## 3. AWS services used

| AWS service / tool | Purpose in SAI ELECTRONICS |
|---|---|
| Amazon Route 53 | Hosts DNS records for `saivardhan.online` and routes the domain to the application load balancer. |
| AWS Certificate Manager (ACM) | Provides the issued TLS certificate used by the ALB HTTPS listener. |
| Amazon VPC | Provides isolated networking for public, application and database subnets. |
| Public subnets | Place the internet-facing Application Load Balancer across Availability Zones. |
| Private application subnet | Hosts the application EC2 instance without a directly assigned public IPv4 address. |
| Private database subnets | Provide private network placement for the Aurora database. |
| Application Load Balancer (ALB) | Receives website traffic; HTTPS listener uses port 443 and HTTP port 80 redirects to HTTPS. |
| Target Group | Registers the EC2 web server and performs health checks. |
| Amazon EC2 | Runs the Nginx web server that serves the frontend application. |
| Nginx | Serves the HTML, CSS, JavaScript and website assets. |
| Amazon S3 — frontend bucket | Stores frontend assets used for deployment and synchronization to the EC2 web root. |
| Amazon API Gateway (HTTP API) | Exposes HTTP endpoints used by the frontend JavaScript. |
| AWS Lambda | Runs the `sai-electronics-api` backend logic for products, customers, orders and payment workflows. |
| Amazon Aurora MySQL | Stores customer, product, order, order-item and payment-reference data. |
| AWS Secrets Manager | Stores database credentials retrieved by the Lambda function. |
| AWS Systems Manager Session Manager | Provides managed administrative access to the EC2 instance. |
| Amazon CloudWatch Logs | Stores Lambda execution logs, including START, END and REPORT records. |
| AWS CloudTrail | Records AWS account management activity in a multi-Region trail. |
| Amazon S3 — CloudTrail log bucket | Stores CloudTrail audit log files. |
| Amazon Athena | Queries CloudTrail audit data using SQL. |
| Amazon S3 — Athena query-results bucket | Stores Athena query output separately from the CloudTrail source data. |

## 4. Architecture and service connections

The architecture is shown in [SAI_ELECTRONICS_AWS_Architecture.svg](architecture/SAI_ELECTRONICS_AWS_Architecture.svg).

### 4.1 Website request path

1. A customer opens `https://saivardhan.online`.
2. Amazon Route 53 resolves the domain to the internet-facing ALB.
3. The ALB presents the ACM-issued TLS certificate and accepts HTTPS traffic on port 443. HTTP traffic on port 80 is redirected to HTTPS.
4. The ALB forwards traffic through its target group to the EC2 instance in the private application subnet.
5. Nginx on EC2 serves the frontend files.

### 4.2 Frontend deployment path

1. Website assets are stored in the frontend Amazon S3 bucket.
2. The assets are synchronized to `/usr/share/nginx/html/` on EC2.
3. Nginx serves the synchronized HTML, CSS and JavaScript files to browsers.

### 4.3 API and database path

1. Browser JavaScript sends HTTPS requests to Amazon API Gateway.
2. API Gateway invokes the `sai-electronics-api` Lambda function.
3. Lambda obtains database credentials from AWS Secrets Manager.
4. Lambda connects to Amazon Aurora MySQL over the configured VPC networking and database security-group rules.
5. Aurora stores and returns product, customer, order and order-item records.

### 4.4 Customer order and payment-reference path

1. A customer signs in and selects products.
2. The browser sends the requested product IDs and quantities to the order API.
3. Lambda validates the customer and product availability, calculates the order total using database prices, creates the order and order items, and updates product stock.
4. The application displays UPI payment instructions and accepts a transaction reference.
5. The admin workflow lists submitted payment references for manual review.

**Payment handling:** Submission of a UPI reference is not itself confirmation that funds were received. Payment must be reconciled against the merchant bank/UPI record before the order is treated as paid.

## 5. Monitoring, logging and audit analytics

### Amazon CloudWatch

The Lambda log group `/aws/lambda/sai-electronics-api` records function execution. The observed log streams contain Lambda START, END and REPORT entries, including execution duration and memory information.

### AWS CloudTrail

The multi-Region trail `sai-electronics-trail` records account activity and delivers audit files to the CloudTrail S3 bucket.

### Amazon Athena

An Athena table was created for the CloudTrail dataset. The query editor was configured with a separate S3 query-results location using SSE-S3 encryption. A SQL query was run to read event time, event source, event name, Region, source IP address and error code.

## 6. Network and security design

- The ALB is internet-facing and placed in public subnets.
- The application EC2 instance is placed in a private subnet and has no directly assigned public IPv4 address.
- The database is accessed through private VPC connectivity.
- HTTPS is enabled at the ALB using the ACM certificate.
- Database credentials are held in Secrets Manager rather than embedded in frontend code.
- Systems Manager Session Manager is used for managed EC2 administration.
- Security groups control traffic between the ALB, application and database tiers.

## 7. Cost-aware design considerations

- API Gateway and Lambda provide a request-driven backend execution model.
- CloudTrail management events are used for account activity auditing; broad S3 and Lambda data-event logging is not required for the demonstrated setup.
- CloudTrail source logs and Athena query results are stored in separate S3 buckets.
- Athena queries should use date and Region filters where appropriate to limit data scanned.
- S3 lifecycle policies and CloudWatch log retention can be reviewed to manage storage growth.
- EC2, ALB, Aurora and NAT-related resources should be monitored against actual usage and AWS billing.

## 8. Technology summary

**Frontend:** HTML, CSS, JavaScript, Nginx  
**Backend:** Amazon API Gateway (HTTP API), AWS Lambda, Python  
**Database:** Amazon Aurora MySQL  
**Hosting and networking:** Amazon EC2, Amazon VPC, public/private subnets, ALB, Target Group, Route 53  
**TLS and secrets:** AWS Certificate Manager, AWS Secrets Manager  
**Storage and deployment:** Amazon S3, AWS Systems Manager Session Manager  
**Observability and analytics:** Amazon CloudWatch Logs, AWS CloudTrail, Amazon Athena

---

**Project:** SAI ELECTRONICS  
**Architecture pattern:** EC2-hosted web frontend with a serverless API backend and managed relational database.
