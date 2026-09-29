# Smart City Dashboard

A Python-based data analytics dashboard designed to monitor and analyze key aspects of urban life, including **air quality, traffic, water consumption, and energy usage**.

The project uses **NumPy, Pandas, and Streamlit** to transform raw city datasets into interactive visualizations and meaningful insights that support data-driven understanding of sustainable urban development.

---

##  Project Overview

Modern cities generate large amounts of data across transportation, environmental conditions, utilities, and resource consumption. However, raw data alone can be difficult to interpret.

The **Smart City Dashboard** brings these datasets together into a single interactive application. Users can explore city-level trends, compare different areas, analyze resource consumption, and identify potential urban challenges through statistical analysis and visualizations.

The project is primarily aligned with **UN Sustainable Development Goal 11: Sustainable Cities and Communities**, with supporting connections to SDGs related to health, clean water, clean energy, responsible consumption, and climate action.

---

##  Objectives

* Analyze real-world urban datasets using Python.
* Demonstrate practical use of **NumPy and Pandas** for data analysis.
* Build an interactive dashboard using **Streamlit**.
* Visualize important urban trends and comparisons.
* Extract meaningful insights from raw datasets.
* Combine multiple aspects of city management into one dashboard.
* Demonstrate practical Python programming and data-handling skills.

---

##  Key Modules

###  Air Quality

Analyzes environmental conditions using parameters such as:

* AQI
* PM2.5
* PM10
* NO₂
* SO₂
* CO

**Possible analysis:**

* Average AQI by city
* Monthly pollution trends
* City-wise pollution comparison
* AQI category distribution
* Highest pollution levels

---

###  Traffic

Analyzes urban transportation patterns using data such as:

* Vehicle count
* Average speed
* Road
* Time
* Congestion level

**Possible analysis:**

* Peak traffic hours
* Traffic volume by city
* Average vehicle speed
* Congestion comparison
* Weekday vs weekend traffic

---

###  Water

Analyzes urban water consumption and availability using:

* Water consumption
* Water supply
* Population
* Water quality indicators

**Possible analysis:**

* Daily/monthly water consumption
* Per-capita consumption
* Supply vs demand
* City-wise comparison
* Water quality trends

---

###  Energy

Analyzes urban energy usage using:

* Electricity consumption
* Renewable energy
* Non-renewable energy
* Peak demand

**Possible analysis:**

* Energy consumption trends
* Peak demand
* Renewable energy percentage
* City-wise energy comparison
* Renewable vs non-renewable usage

---

##  Dashboard Structure

```text
Smart City Dashboard
│
├── Overview
│   └── Combined city insights
│
├── Air Quality
│   └── Pollution analysis
│
├── Traffic
│   └── Transportation analysis
│
├── Water
│   └── Water resource analysis
│
├── Energy
│   └── Energy consumption analysis
│
└── Reports
    └── Data tables and summaries
```

---

## Technology Stack

| Technology       | Purpose                                              |
| ---------------- | ---------------------------------------------------- |
| **Python**       | Core programming language                            |
| **NumPy**        | Numerical and statistical calculations               |
| **Pandas**       | Data loading, cleaning, transformation, and analysis |
| **Streamlit**    | Interactive web dashboard                            |
| **CSV**          | Dataset storage                                      |
| **Git & GitHub** | Version control and collaboration                    |

---

## Project Structure

```text
SmartCityDashboard/
│
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── air_quality.csv
│   ├── traffic.csv
│   ├── water.csv
│   └── energy.csv
│
├── modules/
│   ├── air_quality.py
│   ├── traffic.py
│   ├── water.py
│   └── energy.py
│
└── utils/
    └── common.py
```

---

## Team Contribution

The project follows a **four-member, four-dataset structure**, where each member is responsible for one urban domain.

| Member                  | Responsibility       | Dataset     |
| ----------------------- | -------------------- | ----------- |
| **Vaishnav Sunil Nair** | Air Quality Analysis | Air Quality |
| **Shreyas Nair**        | Traffic Analysis     | Traffic     |
| **Adithyadev B**        | Water Analysis       | Water       |
| **Kiran S Nair**        | Energy Analysis      | Energy      |

### Individual Responsibilities

Each member is expected to:

1. Obtain and understand their dataset.
2. Clean and prepare the data using Pandas.
3. Perform numerical and statistical analysis using Pandas and NumPy.
4. Create meaningful visualizations.
5. Implement their Streamlit dashboard section.
6. Identify useful insights from the analysis.
7. Integrate their module into the main application.

The final dashboard combines all four modules into a unified **Smart City Analytics Platform**.

---

## Python Concepts Demonstrated

The project demonstrates practical application of:

* Variables and data types
* Conditional statements
* Loops
* Functions
* Lists and dictionaries
* Modules
* Exception handling
* File handling
* CSV processing
* NumPy arrays and calculations
* Pandas DataFrames
* Data filtering
* Data grouping and aggregation
* Data cleaning
* Statistical analysis
* Streamlit components

---

##  Data Analysis Workflow

```text
Raw Dataset
     ↓
Data Loading
     ↓
Data Cleaning
     ↓
Data Transformation
     ↓
Statistical Analysis
     ↓
Visualization
     ↓
Urban Insights
     ↓
Streamlit Dashboard
```

---

##  SDG Alignment

### Primary SDG

### **SDG 11 – Sustainable Cities and Communities**

The project supports data-driven understanding of urban conditions and resource usage, contributing to better planning and sustainable city management.

### Supporting SDGs

**SDG 3 – Good Health and Well-being**

Air-quality monitoring can help identify environmental conditions relevant to public health.

**SDG 6 – Clean Water and Sanitation**

Water consumption and quality analysis supports better understanding of urban water resources.

**SDG 7 – Affordable and Clean Energy**

Energy consumption and renewable-energy analysis can highlight patterns in urban energy use.

**SDG 12 – Responsible Consumption and Production**

Water and energy consumption analysis encourages awareness of resource utilization.

**SDG 13 – Climate Action**

Air-quality and energy data can provide insights into environmental and climate-related trends.

---

##  Example Insights

The dashboard should not only display graphs. It should help users understand **what the data means**.

Examples:

> **"City A recorded the highest average AQI during the selected period."**

> **"Traffic volume reaches its highest level between 8 AM and 10 AM."**

> **"City B has higher per-capita water consumption than the other monitored cities."**

> **"Renewable energy accounts for 41% of the recorded energy consumption in City C."**

These insights are generated from the underlying datasets and analysis rather than being manually written into the dashboard.

---

##  Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd smart-city-dashboard
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The dashboard will open in your browser.

---

##  Requirements

The project's `requirements.txt` currently includes:

```text
numpy
pandas
streamlit
```

Additional libraries may be added if required by the final implementation.

---

##  Future Improvements

Possible future extensions include:

* Additional city datasets
* Interactive geographical maps
* Real-time data integration
* Automated report generation
* Advanced statistical analysis
* Additional urban indicators
* City-to-city comparison
* Historical trend analysis

---

##  Academic Context

**Course:** Introduction to Python
**Program:** CSE – Artificial Intelligence
**Semester:** S3
**Institution:** Amrita Vishwa Vidyapeetham

This project focuses on applying Python programming, numerical computing, data manipulation, and visualization techniques to a practical urban analytics problem.
