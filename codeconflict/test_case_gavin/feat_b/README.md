# Developer 2: Responsive Layout Feature

## Description

This branch contains Developer 2's implementation of responsive layout features for the user profile component.

## Changes Made

1. Added responsive design functionality
   - Added screen size detection with useEffect and resize listener
   - Created three layout sizes: mobile, tablet, and desktop
   - Dynamically applies appropriate styles based on screen width
2. Enhanced component structure
   - Reorganized elements for better responsive layout
   - Added wrapper div for contact information
   - Modified bio display for mobile devices
3. Improved CSS with responsive classes
   - Added size-specific avatar styles
   - Created width constraints for different device sizes
   - Optimized button width and text size for mobile

## Usage

```jsx
import UserProfile from "./UserProfile";

const user = {
  name: "Jane Doe",
  avatar: "/path/to/avatar.jpg",
  email: "jane.doe@example.com",
  role: "Developer",
  joinDate: "Jan 1, 2023",
  lastActive: "Today",
  bio: "Frontend developer with 5 years of experience.",
};

function App() {
  return <UserProfile user={user} />;
}
```

The component automatically adapts to the screen size without requiring additional props.
