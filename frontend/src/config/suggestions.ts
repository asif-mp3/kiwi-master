// Follow-up query suggestions shown in voice mode and chat
export const FOLLOW_UP_SUGGESTIONS = [
  // Trend Analysis
  "Are sales increasing or decreasing in Chennai?",
  "Which state shows a declining sales trend?",
  "Which category shows consistent growth across months?",
  "Are profits stable or volatile over time?",
  "Which month had an unusual spike in sales?",
  "Is revenue seasonally higher in certain months?",
  "Which branch shows declining performance?",
  "Which category is losing revenue month by month?",
  "Are costs rising faster than revenue?",
  "Which quarter performed the worst overall?",

  // Follow-up Chains
  "What is the total sales amount in Chennai?",
  "Is it higher or lower compared to Bangalore?",
  "Which category has the highest total sales?",
  "Did sales for this category increase or decrease over time?",
  "Which branch has the highest revenue overall?",
  "Is this branch performing better or worse than the average branch?",
  "Which payment mode has the highest sales amount?",
  "Has the usage of this payment mode increased over the months?",
  "Which SKU has the highest total revenue?",
  "Is this SKU's sales trend consistently increasing?",
  "Compare total sales between November and December",
  "If the same trend continues, what could be the projected sales for January?",
  "Show sales trend for Chennai across months",
  "Based on this trend, estimate next month's sales",
  "Show category-wise sales for the last three months",

  // Projection Questions
  "If the top category continues this pattern, what is the expected sales next month?",
  "Project the next month's revenue assuming similar change",
  "If this trend continues, what could be the sales next month?",
  "What could be the projected sales for January?",
  "Estimate next month's sales based on current trend",
  "Based on this trend, what's the forecast for next quarter?",
  "If growth continues, when will we reach 1 crore revenue?",
  "What's the expected profit margin next month?",
  "Project year-end revenue based on current performance",
  "Estimate Q4 sales if current trend persists",

  // Employee/HR Queries
  "How many employees do we have?",
  "Show staff in Sales department",
  "How many managers are there?",
  "What is the average salary?",
  "Employees in Tamil Nadu",
  "Who is on leave?",
  "How many employees are on probation?",
  "Active staff count",
  "IT department employees",
  "Show employees by department",
  "Who has the highest salary?",
  "Average salary by department",
  "How many employees joined in 2024?",
  "Show designation-wise employee count",
  "Employees from Karnataka",

  // Attendance Queries
  "Today's attendance percentage",
  "HR department attendance",
  "Average hours worked",
  "Half day count",
  "Show attendance by department",
  "Which department has best attendance?",
  "How many employees were present today?",
  "Who worked more than 9 hours?",
  "Show check-in times for IT department",
  "Average working hours by department",

  // Payroll Queries
  "Show net salary by department",
  "Average bonus amount",
  "Total deductions this month",
  "Highest paid employee",
  "Department-wise total payroll",
  "Monthly payroll cost",

  // Sales Analysis
  "What is the total sales this month?",
  "Show me top 5 products by revenue",
  "Which month recorded the highest total profit?",
  "How many transactions were made using UPI?",
  "Show month-over-month growth",
  "What's the average order value?",
  "Which product category generates most revenue?",
  "Compare sales across different regions",
  "What's the profit margin by category?",
  "Show sales distribution by payment method",
  "Which branch has the lowest sales?",
  "What's the total revenue this quarter?",
  "Show top 10 selling products",
  "Which state contributes most to revenue?",
  "What's the conversion rate by channel?",

  // Advanced Analytics
  "Which state moved from top 3 to bottom 3 in revenue?",
  "Show correlation between marketing spend and sales",
  "What's the customer retention rate?",
  "Identify products with declining margins",
  "Which branch has the highest growth rate?",
  "Show seasonal patterns in sales data",
  "What's the average customer lifetime value?",
  "Identify underperforming product categories",
  "Show year-over-year growth comparison",
  "What's the inventory turnover ratio?",

  // Miscellaneous
  "Show me the data summary",
  "What tables are available?",
  "Give me an overview of the dataset",
  "What time period does the data cover?",
  "How many records are in the database?",
  "Show me sample data",
  "What metrics can I query?",
  "Explain the data structure",
  "What's the data quality like?",
];

export function getRandomSuggestions(count: number = 3): string[] {
  const shuffled = [...FOLLOW_UP_SUGGESTIONS].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}
