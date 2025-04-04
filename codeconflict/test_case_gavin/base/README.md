# Initial Code Base

## Description

This is the starting code base that both developers begin with. It contains a basic React user profile component without any advanced features.

## Components

- `UserProfile.jsx`: A simple React component that displays user information
- `UserProfile.css`: Basic styling for the user profile component

## Features

- Displays user avatar, name, email, and role
- Has a "Show More" button that expands to show additional user details
- Uses basic styling with a clean, light interface

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
