# EcoTrack AI Requirements

**Source:** Software Requirements Specification (SRS), Version 1.0  
**Project:** Smart Plastic Waste Monitoring and Collection Platform  
**Prepared for:** Smart India Hackathon (SIH)

## 1. Product Scope

EcoTrack AI is an AI-assisted web/mobile platform that connects citizen plastic-waste reports with administrative review, collection assignment, field progress tracking, and completion verification.

### User Roles

- **Citizen:** Creates reports, views report status, and receives status updates.
- **Administrator:** Reviews reports, manages users, assigns collection work, verifies evidence, and monitors analytics.
- **Collection Team:** Views assigned tasks, updates collection progress, and submits completion evidence.

## 2. Functional Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | The system shall support secure user registration and login with role-aware authentication. | Must |
| FR-02 | A citizen shall be able to create a waste report with an uploaded image, location, and optional description. | Must |
| FR-03 | The system shall analyze an uploaded image and store an estimated result indicating whether plastic waste is present. | Must |
| FR-04 | The system should classify detected waste as bottles, bags, wrappers, containers, or other plastic waste when supported by the AI model. | Should |
| FR-05 | The system shall capture or accept latitude and longitude coordinates for each report. | Must |
| FR-06 | The system shall display reported locations on an interactive map with status and category filters. | Must |
| FR-07 | The administrator dashboard shall display reports, statuses, locations, categories, and collection progress. | Must |
| FR-08 | Administrators shall be able to review reports and accept, reject, flag, or update their status. | Must |
| FR-09 | Administrators shall be able to assign accepted reports to eligible collection team members. | Must |
| FR-10 | Collection team members shall be able to view assigned tasks and update task progress. | Must |
| FR-11 | Collection team members should be able to upload an after-collection image or other completion evidence. | Should |
| FR-12 | Administrators shall be able to verify or reject submitted completion evidence. | Must |
| FR-13 | The system should provide notifications or status messages when report or task states change. | Should |
| FR-14 | The dashboard shall support searching and filtering by status, category, date, and location where applicable. | Must |
| FR-15 | The system shall provide statistics for total, pending, collected, and category-wise reports. | Must |
| FR-16 | The backend shall persist users, reports, assignments, AI results, and verification records with appropriate relationships. | Must |

## 3. Report Workflow

The default report lifecycle is:

`Reported -> AI Analyzed -> Reviewed -> Assigned -> In Progress -> Collected -> Verified`

Administrators may reject invalid, duplicate, or insufficient reports. A prototype may simplify intermediate states while preserving the core flow.

## 4. Data Requirements

### User

- `user_id`
- `name`
- `contact_or_login_identifier`
- `role`
- Authentication metadata

### Waste Report

- `report_id`
- `user_id`
- Image reference
- AI result
- Category
- `latitude`
- `longitude`
- Description
- Timestamp
- Status

### Assignment

- `assignment_id`
- `report_id`
- `collector_id`
- `assigned_at`
- Task status

### Verification

- `verification_id`
- `report_id`
- Evidence image reference
- `verified_by`
- Verification status
- Timestamp

### Analytics

Analytics shall be derived from stored reports and collection records, including counts, category distribution, status distribution, and collection progress.

## 5. Non-Functional Requirements

- **Performance:** Normal report and dashboard operations should respond within an acceptable time for prototype load; AI inference should be minimized.
- **Security:** Credentials shall be handled securely, and role-based access shall protect administrative and collection functions.
- **Privacy:** Only necessary personal and location data shall be collected and stored securely.
- **Availability:** Temporary service failures shall be handled gracefully.
- **Usability:** Interfaces shall be simple, mobile-friendly, and understandable to first-time users.
- **Scalability:** The architecture should support additional users, reports, collection teams, and AI models without major redesign.
- **Maintainability:** Frontend, backend, database, storage, and AI components should remain modular.
- **Reliability:** Uploads and inputs shall be validated, and successfully submitted reports shall not be lost.
- **Accessibility:** Important actions and information shall use readable text, clear controls, and responsive layouts.

## 6. External Interfaces

- Responsive citizen reporting interface for mobile and desktop.
- Login and registration interface.
- Image upload, description, and location controls.
- Interactive map for report locations.
- Admin dashboard with tables, filters, charts, and status controls.
- Collection-team task interface.
- REST API between frontend and backend services.
- Persistent database and file storage.
- AI image-analysis service.
- Map/GPS service.
- Optional notification service.

## 7. Security Controls

- Hash passwords using a modern password-hashing algorithm.
- Validate file type, file size, image content, and all user inputs.
- Enforce authorization on every protected API endpoint.
- Restrict administrator and collection-team actions by role.
- Use HTTPS in production.
- Keep private API keys and service credentials out of frontend source code.

## 8. Acceptance Criteria

- A registered user can submit a waste image and location successfully.
- The system produces and stores an AI analysis result.
- The report appears on the administrator dashboard and map.
- An administrator can review and assign an accepted report.
- A collection team member can view the assigned task and update its status.
- Completion evidence can be submitted and verified or rejected.
- Dashboard statistics reflect stored report and collection data.
- Unauthorized users cannot access protected administrative functions.

## 9. Recommended Prototype Stack

- **Frontend:** HTML, CSS, JavaScript, or React
- **Backend:** Python Flask or FastAPI
- **Database:** Firebase/Firestore, PostgreSQL, or MongoDB
- **AI:** Python computer-vision classification or object-detection model
- **Maps:** OpenStreetMap or another suitable mapping API
- **Hosting:** Vercel for frontend and a suitable cloud service for backend/API and AI inference
