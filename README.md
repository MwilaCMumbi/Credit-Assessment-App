VZ Credit Score App
Credit risk assessment tool that calculates scores and recommends financial products.

Installation

pip install streamlit sqlite3
streamlit run Credit-Score.py

Scoring Factors
Credit History: 30%

Income Stability: 25%

Banking Access: 20%

Location: 15%

Referral: 10%

Risk Levels
8+: Low Risk → All products

5-7.9: Medium Risk → Mid-value products

3-4.9: High Risk → Low-value products

Below 3: Rejected → No products

Core Calculation

score = (history*0.30 + income*0.25 + 
         banking*0.20 + location*0.15 + 
         referral*0.10)


📜 License
MIT License - Free for commercial and personal use
