# Developer 1: Dark Mode Feature

## Description

This branch contains Developer 1's implementation of a dark mode feature for the user profile component.

## Changes Made

1. Added theme switching functionality
   - Added `theme` prop with default value 'light'
   - Added state to track current theme
   - Added toggle function to switch between light/dark modes
2. Enhanced styling with theme support

   - Added theme-specific CSS classes
   - Added transition effects for smooth theme changes
   - Modified button styling to reflect current theme

3. Added UI controls
   - Added a theme toggle button (moon/sun icon)
   - Positioned the toggle button in the header

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
  // Can set initial theme to 'light' or 'dark'
  return <UserProfile user={user} theme="light" />;
}
```
