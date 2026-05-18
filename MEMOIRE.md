# Project Report Submitted at

# Mohamed Boudiaf University - M'sila

**Faculty of Mathematics and Computer Science**  
**Department of Computer Science**

---

**For the partial fulfillment of the requirements for the Bachelor's Degree in Computer Science**

By

**Sailaa Mohammed Radhwen**

---

# Intelligent Sales Overview and Forecasting System

---

Supervised by:  
**Cherait Hanan**

**May 2026**

\newpage

## Dedication

I dedicate this work to my parents, my family, and everyone who supported me during my studies.

\newpage

## Acknowledgements

I thank Allah for giving me the strength to complete this work.

I sincerely thank my supervisor, **Mrs. Cherait Hanan**, for her guidance and support.

I also thank the teachers of the Department of Computer Science at the University of M'sila.

\newpage

## Index

| Section | Page |
|---------|------|
| General Introduction | 1 |
| Chapter 1: Work Context | 3 |
| Chapter 2: System Design | 7 |
| Chapter 3: Implementation | 12 |
| General Conclusion | 18 |
| References | 19 |
| Abstract | 20 |

\newpage

## General Introduction

Data analysis has become essential for modern companies because it helps them understand performance, predict trends, and support decision-making.

In Algeria, many small and medium enterprises still face difficulties in using advanced analytics tools because of high cost, technical complexity, and lack of integrated solutions. Most existing tools are either expensive or not adapted to the local context.

For this reason, this project proposes an intelligent web-based system for sales analysis and forecasting. The platform combines forecasting, customer segmentation, product recommendations, and sentiment analysis in one application.

This report is organized into three chapters. The first chapter presents the project context. The second chapter explains the design of the system. The third chapter presents the implementation and testing.

---

\newpage

# Chapter One: Work Context

## 1.1 Introduction

This chapter introduces the general context of the project and explains why Sales Intelligence is important for SMEs.

## 1.2 Definition of Sales Intelligence

Sales Intelligence is the use of sales, customer, and market data to improve business decisions. It helps companies analyze performance and predict future demand.

Its main functions include:

- sales forecasting,
- customer segmentation,
- customer lifetime value analysis,
- product recommendation,
- sentiment analysis.

## 1.3 Importance for SMEs

Sales Intelligence helps SMEs to:

- improve decision-making,
- reduce inventory problems,
- identify valuable customers,
- improve customer satisfaction,
- and increase profitability.

## 1.4 Problems Faced by SMEs in Algeria

The main difficulties are:

- lack of affordable analytics tools,
- dependence on manual analysis,
- absence of forecasting tools,
- fragmented data,
- weak support for Arabic text analysis.

## 1.5 Existing Solutions

Some existing tools offer reporting and analytics, but they remain expensive or incomplete for the needs of SMEs.

| Feature | Existing Tools | Our System |
|---------|----------------|------------|
| Price | Expensive | Affordable |
| Forecasting | Limited | Prophet forecasting |
| Segmentation | Partial | Automated RFM |
| Recommendations | Rare | Apriori |
| Arabic sentiment | Not supported | Supported |
| Multi-tenant mode | Limited | Available |

## 1.6 Proposed Solution

The proposed solution is an **Intelligent Sales Overview and Forecasting System**, a web-based SaaS platform dedicated to SMEs.

The system offers:

- sales forecasting with Prophet,
- customer segmentation using RFM,
- customer lifetime value calculation,
- product recommendations,
- English and Arabic sentiment analysis,
- role-based access control,
- and an interactive dashboard.

## 1.7 Conclusion

This chapter presented the project context and the proposed solution. The next chapter describes the design of the system.

---

\newpage

# Chapter Two: System Design

## 2.1 Introduction

This chapter presents the design of the system through use cases, database modeling, and architecture.

## 2.2 Use Case Study

The system contains three actors:

- Admin
- BranchManager
- System

The main use cases are:

- Register
- Login
- Logout
- Upload Data
- View Dashboard
- View Forecasting
- View Segmentation
- View Recommendations
- View Sentiment Analysis
- Manage Users
- Manage Branches
- Validate Uploaded Data

These use cases can be grouped into three categories. The first category concerns secure access to the platform through registration, login, and logout. The second category concerns data management, where users upload business files and the system validates their structure and content before processing. The third category concerns analytical consultation and administration, where authorized users explore dashboards, forecasting, segmentation, recommendations, sentiment results, and management functions.

### 2.2.1 Main Use Cases

| Use Case | Actor | Description |
|----------|-------|-------------|
| Register | Admin, BranchManager | Create a new account to access the platform |
| Login | Admin, BranchManager | Access the system securely |
| Logout | Admin, BranchManager | End the current session securely |
| Upload CSV files | Admin, BranchManager | Import business data |
| Validate uploaded data | System | Check file format, required columns, and data consistency before analysis |
| View dashboard | Admin, BranchManager | Consult KPIs and charts |
| Forecast sales | Admin, BranchManager | View future predictions |
| View segmentation | Admin, BranchManager | Consult customer classification results |
| View recommendations | Admin, BranchManager | Consult product association suggestions |
| View sentiment analysis | Admin, BranchManager | Review customer opinion analysis results |
| Manage users | Admin | Create and update accounts |
| Manage branches | Admin | Create and supervise branch structure inside the company |

### 2.2.2 Sequence Overview

The main sequence is as follows:

1. The Admin or BranchManager logs in.
2. The System verifies the credentials.
3. The Admin or BranchManager uploads CSV files.
4. The System stores the data.
5. The System runs the analysis pipeline.
6. The results are displayed on the dashboard.

### 2.2.3 Main Classes

The principal classes are:

- User
- Company
- Branch
- ForecastResult
- RFMResult
- SentimentResult
- Notification

## 2.3 Database Design

The application uses SQLite in development and SQLAlchemy as ORM. The main tables are:

| Table | Role |
|-------|------|
| users | stores user accounts |
| companies | stores tenant data |
| branches | stores company branches |
| forecast_results | stores forecasting results |
| rfm_results | stores segmentation results |
| sentiment_results | stores sentiment results |
| notifications | stores alerts |

### 2.3.1 Relationships

- One company has many users.
- One company has many branches.
- One company has many analysis results.
- One branch belongs to one company.
- One user belongs to one company and optionally one branch.

## 2.4 System Architecture

The application follows a three-tier architecture:

1. **Presentation Layer**: React + TypeScript + Tailwind CSS
2. **Application Layer**: FastAPI backend
3. **Data Layer**: SQLite database + tenant storage

The system also uses a multi-tenant structure to isolate data between companies and branches.

## 2.5 Conclusion

This chapter presented the design of the system. The next chapter describes the implementation phase.

---

\newpage

# Chapter Three: Implementation

## 3.1 Introduction

This chapter presents the implementation of the application, the tools used, the interfaces, and the testing phase.

## 3.2 Development Environment

### 3.2.1 Hardware Specifications

| Component | Specification |
|-----------|---------------|
| Processor | Intel Core i5 or equivalent |
| RAM | 8 GB |
| Storage | 256 GB SSD |
| Operating System | Windows |

### 3.2.2 Software Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python, FastAPI, SQLAlchemy, Uvicorn |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Machine Learning | Prophet, scikit-learn, TextBlob, Transformers, mlxtend |
| Security | JWT, bcrypt |
| Deployment | Docker, Docker Compose, Nginx |

## 3.3 The Developed Application

### 3.3.1 Database Implementation

The database was implemented with SQLAlchemy and contains the main tables needed for users, companies, branches, forecasting, segmentation, sentiment analysis, and notifications.

### 3.3.2 User Interfaces

The application contains the following main pages:

- Authentication page
- Dashboard
- Sales analytics page
- Forecasting page
- Segmentation page
- Recommendations page
- Sentiment page
- Inventory page
- Upload page
- Settings page

### 3.3.3 Main Modules

**Dashboard**: displays KPIs, charts, and alerts.  
**Forecasting**: shows future sales predictions using Prophet.  
**Segmentation**: classifies customers with RFM analysis.  
**Recommendations**: identifies products often bought together.  
**Sentiment Analysis**: analyzes customer reviews in English and Arabic.  
**Upload Module**: imports CSV files and starts the processing pipeline automatically.

## 3.4 System Testing

The application was tested using unit and integration tests.

| Test Type | Tool | Goal |
|-----------|------|------|
| API tests | pytest | verify endpoints |
| ML tests | pytest | verify analysis scripts |
| Integration tests | PowerShell script | verify branch isolation |

### 3.4.1 Main Test Scenarios

- login with valid credentials,
- login with invalid credentials,
- access without token,
- upload valid CSV files,
- consult dashboard data,
- verify branch permissions.

## 3.5 Conclusion

This chapter described the implementation of the platform and confirmed that the system was successfully developed and tested.

---

\newpage

## General Conclusion

This project presented the development of an intelligent web platform for sales analysis and forecasting dedicated to SMEs.

The system combines forecasting, segmentation, recommendations, sentiment analysis, and dashboard visualization in one platform. It also supports multi-tenant management and role-based access control.

The final result is a practical and affordable solution that can help companies improve decision-making and better understand their business data.

As future work, the platform can be improved by adding real-time analytics, mobile access, and more advanced forecasting models.

---

\newpage

## References

1. Taylor, S.J. & Letham, B. (2018). Forecasting at Scale.
2. Agrawal, R. & Srikant, R. (1994). Fast Algorithms for Mining Association Rules.
3. Antoun, W. et al. (2020). AraBERT: Transformer-based Model for Arabic Language Understanding.
4. FastAPI Documentation.
5. React Documentation.
6. SQLAlchemy Documentation.
7. Docker Documentation.

---

\newpage

## Abstract

This work presents an Intelligent Sales Overview and Forecasting System designed for Small and Medium Enterprises. The platform integrates sales forecasting, customer segmentation, product recommendations, and sentiment analysis in one web application. It is built with FastAPI for the backend, React for the frontend, and machine learning libraries such as Prophet and AraBERT. The system helps companies analyze data, improve decisions, and obtain useful business insights.

**Keywords**: Sales Intelligence, Forecasting, RFM, Sentiment Analysis, SaaS, Multi-tenant.

---

## الملخص

يعرض هذا العمل نظاما ذكيا لتحليل وتنبؤ المبيعات موجها للمؤسسات الصغيرة والمتوسطة. النظام عبارة عن منصة ويب من نوع SaaS تدمج التنبؤ بالمبيعات، تجزئة العملاء، توصيات المنتجات، وتحليل المشاعر في تطبيق واحد. تم تطويره باستعمال FastAPI في الخلفية وReact في الواجهة مع الاعتماد على مكتبات تعلم آلي مثل Prophet وAraBERT. يساعد النظام الشركات على تحليل بياناتها وتحسين قراراتها واستخراج مؤشرات مفيدة.

**الكلمات المفتاحية**: ذكاء المبيعات، التنبؤ، RFM، تحليل المشاعر، SaaS، متعدد المستأجرين.
