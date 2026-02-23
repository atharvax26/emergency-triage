# Accessibility Compliance

This document outlines the accessibility features implemented in the Emergency Triage Assistant application.

## WCAG 2.1 Level AA Compliance

### 1. Large Touch Targets
- **Minimum size**: All interactive elements meet 44x44px minimum (WCAG 2.5.5)
- **Emergency button**: 80px height for critical actions
- **Primary buttons**: 64px height for main actions
- **Standard buttons**: 56px height for secondary actions
- **Touch-friendly spacing**: 12px padding minimum

### 2. High Contrast
- **Text contrast**: 
  - Light mode: Black text (#000000) on white background (#FFFFFF) = 21:1 ratio
  - Dark mode: White text (#FFFFFF) on dark background (#1A1A1A) = 15.8:1 ratio
- **Severity colors**: Enhanced saturation for better visibility
  - Critical: Red with 100% saturation
  - High: Orange with 100% saturation
  - Medium: Yellow with 100% saturation (dark text for contrast)
  - Low: Green with 100% saturation
- **Borders**: 2px minimum width for clear visual separation
- **Focus indicators**: 3px solid outline with 2px offset

### 3. Keyboard Navigation
- **Skip to main content**: Link appears on first Tab press
- **Focus visible**: Clear 3px outline on all focusable elements
- **Logical tab order**: Follows visual layout
- **ARIA labels**: All interactive elements have descriptive labels
- **Keyboard shortcuts**: All mouse actions accessible via keyboard

### 4. Screen Reader Support
- **Semantic HTML**: Proper use of header, main, nav, button elements
- **ARIA labels**: Descriptive labels for all buttons and controls
  - Emergency button: "Activate emergency response"
  - Analyze button: "Analyze patient and generate triage assessment"
  - Queue actions: "Start triage for [patient name], [severity] severity"
- **ARIA current**: Navigation indicates current page
- **ARIA hidden**: Decorative icons hidden from screen readers
- **Role attributes**: main, navigation roles explicitly defined

### 5. Text and Typography
- **Base font size**: 16px (1rem) minimum
- **Line height**: 1.6 for improved readability
- **Font weight**: 600 (semibold) for important text
- **Button text**: 
  - Emergency: 20px (1.25rem)
  - Primary: 18px (1.125rem)
  - Standard: 16px (1rem)

### 6. Color Independence
- **Not relying on color alone**: 
  - Severity indicated by text labels AND color
  - Icons accompany color-coded elements
  - Status shown with text AND visual indicators
- **Text alternatives**: All visual information has text equivalent

### 7. Emergency Usability
- **Critical actions prominent**: Emergency button always visible, large, high contrast
- **Clear visual hierarchy**: Most important information first
- **No distractions**: Zero animations or transitions
- **Instant feedback**: No delays in UI response
- **Error prevention**: Confirmation dialogs for critical actions

### 8. Motion and Animation
- **Zero animations**: All animations disabled globally
- **Zero transitions**: All transitions disabled globally
- **Instant state changes**: Immediate visual feedback
- **Respects prefers-reduced-motion**: Already implemented via global disable

### 9. Form Accessibility
- **Labels**: All inputs have associated labels
- **Required fields**: Clearly marked
- **Error messages**: Clear and descriptive
- **Input types**: Appropriate HTML5 input types
- **Autocomplete**: Enabled where appropriate

### 10. Mobile and Touch
- **Responsive design**: Works on all screen sizes
- **Touch targets**: Minimum 48x48px for mobile
- **No hover-only**: All interactions work on touch devices
- **Pinch to zoom**: Not disabled

## Testing Recommendations

### Manual Testing
1. **Keyboard navigation**: Tab through entire application
2. **Screen reader**: Test with NVDA, JAWS, or VoiceOver
3. **High contrast mode**: Test in Windows High Contrast
4. **Zoom**: Test at 200% zoom level
5. **Touch**: Test on tablet/mobile devices

### Automated Testing
1. **axe DevTools**: Run accessibility audit
2. **Lighthouse**: Check accessibility score
3. **WAVE**: Web accessibility evaluation tool

## Known Limitations
- Voice input requires browser support (not WCAG requirement)
- Some medical terminology may be complex for all users
- Real-time features require JavaScript enabled

## Future Improvements
- Add language selection for internationalization
- Implement voice output for critical alerts
- Add customizable text size controls
- Provide simplified language mode
