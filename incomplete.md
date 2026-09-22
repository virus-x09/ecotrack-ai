# Incomplete SRS Requirements

While our Backend API fulfills almost all functional requirements from the `SRS.pdf` document, there are several **Frontend UI components** and **Future Enhancements** that are currently incomplete.

## 1. Missing Frontend User Interfaces
Although the backend endpoints are ready for these features, we have not yet built the web pages (HTML/JS) for them:

- **[FR-07] Admin Dashboard UI**: There is no webpage for administrators to log in, view analytics (`/analytics`), or see the overarching map of all reports.
- **[FR-08] Report Review UI**: There is no interface for admins to click on a pending report and approve/reject it.
- **[FR-09] Task Assignment UI**: There is no interface for admins to assign a reviewed report to a specific collection team member.
- **[FR-12] Verification UI**: There is no interface for admins to view the "after-collection" evidence image uploaded by collectors and verify the task is complete.
- **[FR-14] Search and Filtering UI**: The frontend does not currently have search bars, date pickers, or category dropdowns to filter the reports.

## 2. Incomplete Future Enhancements (Section 12)
As outlined in Section 12 of the SRS, the following advanced features have not been started yet:

- **Real-Time Route Optimization:** Automatically routing collection teams based on proximity to reports.
- **Duplicate-Report Detection:** Automatically flagging if two users take a photo of the exact same trash pile.
- **Heatmaps:** A specialized map view highlighting high-waste areas using a heatmap overlay.
- **Reward / Gamification System:** Giving citizens points, badges, or rewards for verified reports.
- **Municipal & NGO Integration:** Automated reporting directly to local government bodies.
- **Predictive Analytics:** Forecasting where waste hotspots will form in the future.

> [!NOTE]  
> If you'd like to prioritize any of these incomplete items (such as building the Admin Dashboard UI), let me know and we can start working on it!
