# Sample Datasets for report-assist

This directory contains 5 curated tabular datasets designed to stress-test **report-assist** across code generation, data visualization, and multi-agent bias debate (**The Optimistic**, **The Pessimistic**, **The Skeptic**, and **Neutral Arbitrator**).

---

## 1. Telco Customer Churn (`telco_churn.csv`)
- **Domain**: SaaS / Subscription Economics / Retention
- **Records**: 7,043 rows | 21 features
- **Key Columns**: `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `InternetService`, `PaymentMethod`, `Churn`
- **Recommended Prompt**:
  > *"Analyze customer churn drivers. Investigate whether customers on month-to-month contracts and fiber optic internet represent a fatal churn risk or an upsell opportunity, and evaluate if long-term contract discounts can increase net customer lifetime value."*
- **Persona Perspectives**:
  - **The Optimistic**: Focuses on long-tenure cohorts with high retention; advocates upselling high-margin add-ons (streaming, device protection) and premium speed tiers.
  - **The Pessimistic**: Flags alarming ~42% month-to-month churn and high attrition rates when monthly bills exceed $70; warns of severe customer and cash flow bleed.
  - **The Skeptic**: Points out survivorship bias (tenure is endogenous because early churners have already dropped out) and questions whether discounts truly alter churn behavior or simply subsidize customers who would stay anyway.

---

## 2. California Housing Valuation (`california_housing.csv`)
- **Domain**: Real Estate / Urban Economics / Wealth & Demographic Analysis
- **Records**: 20,640 rows | 10 features
- **Key Columns**: `median_income`, `housing_median_age`, `total_rooms`, `population`, `median_house_value`, `ocean_proximity`
- **Recommended Prompt**:
  > *"Analyze the relationship between median income, coastal proximity, and housing values. Are current high valuations fundamentally supported by local incomes, or are coastal regions exhibiting signs of an unsustainable asset bubble?"*
- **Persona Perspectives**:
  - **The Optimistic**: Highlights geographic scarcity, strong income fundamentals, and durable long-term appreciation in coastal clusters.
  - **The Pessimistic**: Emphasizes stretched price-to-income multiples, aging housing stock, and affordability stress that leaves the market fragile to rate shocks.
  - **The Skeptic**: Warns about severe right-censoring in the target variable (`median_house_value` artificially capped at $500,001), spatial autocorrelation, and aggregate census-block ecological fallacies.

---

## 3. Medical Insurance & Health Costs (`insurance_charges.csv`)
- **Domain**: Actuarial Underwriting / Healthcare / Risk Modeling
- **Records**: 1,338 rows | 7 features
- **Key Columns**: `age`, `sex`, `bmi`, `children`, `smoker`, `region`, `charges`
- **Recommended Prompt**:
  > *"Examine how smoking status and BMI interact to drive medical insurance charges. Can an insurer safely expand coverage by adjusting premiums by age, or do lifestyle risk factors create catastrophic tail risk?"*
- **Persona Perspectives**:
  - **The Optimistic**: Points out that the majority of policyholders are non-smokers generating consistent, predictable margins with low claims.
  - **The Pessimistic**: Stresses the severe non-linear surge in claim costs for smoking policyholders with BMI > 30, which can wipe out underwriting reserves.
  - **The Skeptic**: Flags critical omitted variables (prior health conditions, occupation, family medical history) and cautions against assuming linear relationships without interaction terms.

---

## 4. Multi-Asset Market & Commodities (`multi_asset_market.csv`)
- **Domain**: Quantitative Finance / Multi-Asset Portfolio / Macro Trends
- **Records**: 1,243 rows | 39 features
- **Key Columns**: `Date`, `Bitcoin_Price`, `Ethereum_Price`, `Gold_Price`, `Crude_oil_Price`, `Natural_Gas_Price`, `S&P_500_Price`, `Nasdaq_100_Price`, `Nvidia_Price`, `Apple_Price`
- **Recommended Prompt**:
  > *"Analyze the price dynamics and rolling correlations between Bitcoin, Gold, and the Nasdaq 100. Does Bitcoin behave as an inflation hedge like Gold, or does it act as a high-beta proxy for speculative tech equities?"*
- **Persona Perspectives**:
  - **The Optimistic**: Sees structural multi-year upside in tech equities and digital assets with superior compounding returns.
  - **The Pessimistic**: Highlights extreme drawdowns, high downside volatility in crypto, and vulnerability to commodity price shocks.
  - **The Skeptic**: Warns against calculating correlations on non-stationary price series without differencing (log returns), highlighting spurious correlation risks and regime shifts.

---

## 5. Media Advertising & Channel Attribution (`advertising.csv`)
- **Domain**: Marketing Analytics / Media Mix Modeling / ROI
- **Records**: 200 rows | 4 features
- **Key Columns**: `TV`, `radio`, `newspaper`, `sales`
- **Recommended Prompt**:
  > *"Evaluate sales attribution across TV, radio, and newspaper advertising. How should our marketing budget be reallocated to maximize marginal sales efficiency, and is newspaper advertising still viable?"*
- **Persona Perspectives**:
  - **The Optimistic**: Identifies TV and radio as proven growth engines and recommends scaling budget allocation into highest-converting channels.
  - **The Pessimistic**: Highlights diminishing marginal returns on heavy TV spend and notes that newspaper spend shows near-zero independent return, actively wasting capital.
  - **The Skeptic**: Emphasizes lack of temporal lag modeling (advertising effects are not instantaneous), absence of product seasonality controls, and potential multi-collinearity between TV and radio campaigns.
