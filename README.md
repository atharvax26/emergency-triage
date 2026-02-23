# Emergency Triage Assistant

A high-contrast, emergency-first triage UI designed for nurses and ER staff. Features zero clutter, large buttons, and fast usability with both dark and light theme support.

## Features

- **Emergency Intake**: Patient information form with symptom input and voice recognition support
- **Triage Dashboard**: AI-powered severity assessment with color-coded alerts (Critical/High/Medium/Low)
- **Audit Log**: Complete history of triage events and decisions
- **Accessibility**: High-contrast design, large touch targets, glove-friendly interface
- **Theme Support**: Dark and light modes optimized for emergency environments

## Tech Stack

- **React** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **shadcn/ui** component library
- **Vitest** for testing

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```sh
# Clone the repository
git clone <YOUR_GIT_URL>

# Navigate to project directory
cd emergency-triage

# Install dependencies
npm install

# Start development server
npm run dev
```

### Windows Quick Start

For Windows users, simply run the included batch file:

```sh
start-dev.bat
```

This will automatically install dependencies (if needed) and start the development server.

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests
- `npm run lint` - Lint code

## Project Structure

```
emergency-triage/
├── src/
│   ├── components/     # React components
│   ├── hooks/          # Custom React hooks
│   ├── lib/            # Utilities and mock data
│   ├── pages/          # Page components
│   └── test/           # Test files
├── public/             # Static assets
└── start-dev.bat       # Windows quick start script
```

## Accessibility

This application follows accessibility best practices with:
- High contrast color schemes
- Large, touch-friendly buttons
- Keyboard navigation support
- Screen reader compatibility

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for detailed information.

## License

[Add your license here]
