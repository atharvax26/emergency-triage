

# Emergency Triage Assistant — Frontend Plan

## Overview
A high-contrast, emergency-first triage UI with zero clutter, large buttons, and fast usability for nurses and ER staff. Frontend-only with static mock data simulating AI responses. Supports both dark and light themes.

---

## Screens to Build

### 1. Emergency Intake Screen (Home)
- **Patient info form**: Name, age, gender, chief complaint
- **Symptom input**: Large text area for typing symptoms
- **Mic button**: Visible microphone button for voice input (non-functional placeholder with "Coming soon" tooltip)
- **File upload area**: Drag-and-drop zone for patient history / protocol PDFs (UI only, no processing)
- **Submit button**: Large, prominent "Analyze" button that navigates to the Triage Dashboard with mock results
- Design: Minimal, large touch targets, high contrast

### 2. Triage Dashboard
- **Severity score**: Large, color-coded badge (Critical / High / Medium / Low) with prominent visual hierarchy
- **AI recommendation panel**: Mock triage action text (e.g., "Immediate IV access, prepare for intubation")
- **Next-step actions**: Checklist of recommended actions the nurse can confirm or override
- **Patient context summary**: Key details extracted from the intake (displayed as cards)
- **Alert escalation indicator**: Visual alert banner for critical cases
- **Override button**: Allows nurse to override AI suggestion with their own assessment

### 3. Audit Log Screen
- **Table view**: List of past triage events with columns — timestamp, patient ID, severity, action taken, overridden (yes/no)
- **Static mock data**: 5-10 sample audit entries
- **Search/filter**: Basic text filter on the table

---

## Shared Components

### Navigation
- Simple top bar with app title ("Emergency Triage"), screen links (Intake, Dashboard, Audit Log), and theme toggle
- No sidebar — keep it minimal per PRD

### Theme Toggle
- Dark and light mode support with a toggle in the nav bar
- Dark: Dark background, bright red/orange/green alerts
- Light: White background, bold alert colors

### Design Principles (from PRD)
- Zero clutter, no animations
- Large buttons and text for glove-friendly use
- High-contrast colors for severity levels (Red = Critical, Orange = High, Yellow = Medium, Green = Low)
- Emergency-first UX throughout

