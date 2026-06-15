# 📊 Team Progress & Logging Report

I have created a `TEAM_REPORT_TEMPLATE.csv` file in the root directory. This file is designed to be opened directly in **Microsoft Excel** or **Google Sheets** for tracking the team's daily work.

## 📈 Column Definitions

1.  **Date**: The day the work was performed.
2.  **Team Member**: Name of the person (Sabih, Harmain, Jaber, Umer, Rehan).
3.  **Task Category**: The specialized area assigned (e.g., Infrastructure, Bot/UX, AI/Content, Video/TTS, Backend/Auth).
4.  **Issue #**: The corresponding GitHub Issue number (1-5).
5.  **Description of Work**: A brief (1-sentence) summary of the specific task completed.
6.  **Hours Spent**: Decimal value of time spent (e.g., 1.5).
7.  **Status**: 
    *   `Planned`: Not yet started.
    *   `In Progress`: Actively working.
    *   `Blocked`: Stuck due to a technical issue or waiting on someone else.
    *   `Completed`: Task finished and PR submitted.
8.  **PR Link**: Link to the GitHub Pull Request for transparency.
9.  **Blockers/Notes**: Any technical hurdles or help needed from the team.

## 🛠️ How to use with Excel/Google Sheets
1.  Open Excel or Google Sheets.
2.  Go to **File > Import** or **Open**.
3.  Select `TEAM_REPORT_TEMPLATE.csv`.
4.  (Optional) Create a **Pivot Table** to automatically calculate the total hours spent per person or per category.

## 🚀 Recommended Routine
*   **Daily Log**: Each member fills in one row at the end of their workday.
*   **Weekly Review**: Sabih (Integrator) reviews the sheet every Friday to check for blockers and update the main project roadmap.
