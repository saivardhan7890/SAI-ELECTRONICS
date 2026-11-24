# SAI ELECTRONICS

**AWS E-Commerce Platform with Serverless APIs and Cost-Aware Audit Analytics**

A full-stack electronics e-commerce demonstration deployed on AWS. The web frontend is served by Nginx on Amazon EC2 behind an Application Load Balancer, while application APIs run on Amazon API Gateway and AWS Lambda with an Amazon Aurora MySQL database.

## Live application

- Website: https://saivardhan.online
- AWS Region: `us-east-1`

## Architecture at a glance

1. Customers resolve the website domain through Amazon Route 53.
2. HTTPS traffic reaches the Application Load Balancer (ALB), using an AWS Certificate Manager certificate.
3. The ALB forwards web traffic to an EC2 instance running Nginx in a private application subnet.
4. Frontend JavaScript calls Amazon API Gateway.
5. API Gateway invokes the `sai-electronics-api` AWS Lambda function.
6. Lambda accesses Amazon Aurora MySQL and retrieves database credentials from AWS Secrets Manager.
7. Frontend assets are stored in Amazon S3 and synchronized to the EC2 web root.
8. Amazon CloudWatch collects Lambda execution logs.
9. AWS CloudTrail records account activity and delivers audit logs to Amazon S3; Amazon Athena is used to query the CloudTrail data.

See the [AWS architecture diagram](docs/architecture/SAI_ELECTRONICS_AWS_Architecture.svg) and the project documentation in [docs/](docs/).

## AWS services and tools

| Service | Role in the project |
|---|---|
| Amazon Route 53 | Public DNS for the application domain |
| AWS Certificate Manager (ACM) | TLS certificate used by the ALB HTTPS listener |
| Amazon VPC | Network isolation and subnet layout |
| Public subnets | Host the internet-facing ALB |
| Private subnet | Hosts the application EC2 instance |
| Application Load Balancer | Routes incoming HTTPS traffic to the web server |
| Amazon EC2 | Hosts Nginx and the static frontend |
| Nginx | Serves the website files |
| Amazon S3 | Stores frontend assets and CloudTrail audit logs; Athena query results use a separate bucket |
| Amazon API Gateway | Exposes application HTTP endpoints |
| AWS Lambda | Runs serverless application API logic |
| Amazon Aurora MySQL | Stores customers, products, orders and order items |
| AWS Secrets Manager | Stores database credentials for backend access |
| Amazon CloudWatch | Stores Lambda execution logs |
| AWS CloudTrail | Records AWS account/API activity |
| Amazon Athena | Queries CloudTrail audit records using SQL |
| AWS Systems Manager Session Manager | Provides managed EC2 administration access |

## Application capabilities

- Customer registration and login
- Electronics catalogue with 50 product entries
- Product photos, categories, prices and stock display
- Shopping cart
- Order creation with stock validation and inventory updates
- Customer order history
- UPI QR payment instructions and transaction-reference submission
- Admin pending-payment review workflow

## Order and payment workflow

1. A customer browses the catalogue, signs in and adds products to the cart.
2. The frontend submits the order request to API Gateway.
3. Lambda validates requested products and stock against Aurora MySQL and records the order.
4. The application displays UPI payment instructions and accepts a transaction reference.
5. An administrator reviews the submitted reference and updates the payment decision through the admin workflow.

**Payment note:** A submitted UPI reference is a request for manual review, not automatic proof that funds were received. Payment should be confirmed against merchant bank/UPI records before an order is treated as paid.

## Logging and audit analytics

- Lambda execution records are available in CloudWatch Logs.
- CloudTrail records AWS account management activity and stores log files in S3.
- Athena provides SQL-based analysis of the CloudTrail log data.
- Athena query results are stored in a separate S3 query-results bucket.

## Security and operational notes

- The website is served over HTTPS through the ALB listener and ACM certificate.
- Database credentials are retrieved from Secrets Manager by the Lambda backend.
- EC2 administration uses Systems Manager Session Manager.
- Customer identity and order ownership must be enforced server-side before production use. The demonstration's browser-held customer ID is not a substitute for token/session authentication and authorization.
- Restrict CORS to the production website origin and limit administrative credentials and permissions.
- Review AWS usage and S3 lifecycle policies regularly to control costs.

## Repository layout

```text
SAI-ELECTRONICS/
├── README.md
└── docs/
    ├── SAI_ELECTRONICS_Final_Project_Documentation.pdf
    ├── SAI_ELECTRONICS_Final_Project_Documentation.docx
    ├── SAI_ELECTRONICS_Final_Handover_Pack.zip
    └── architecture/
        ├── SAI_ELECTRONICS_AWS_Architecture.png
        └── SAI_ELECTRONICS_AWS_Architecture.svg
```

## Project documentation

- [AWS Architecture (SVG)](docs/architecture/SAI_ELECTRONICS_AWS_Architecture.svg)
- [Final Project Documentation (PDF)](docs/SAI_ELECTRONICS_Final_Project_Documentation.pdf)
- [Editable Documentation (DOCX)](docs/SAI_ELECTRONICS_Final_Project_Documentation.docx)

---
Project: **SAI ELECTRONICS**  
Cloud region: **us-east-1**
