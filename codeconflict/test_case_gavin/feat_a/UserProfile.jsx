import React, { useState } from 'react';
import './UserProfile.css';

const UserProfile = ({ user, theme = 'light' }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(theme);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const toggleTheme = () => {
    setCurrentTheme(currentTheme === 'light' ? 'dark' : 'light');
  };

  const themeClass = `user-profile theme-${currentTheme}`;

  return (
    <div className={themeClass}>
      <div className="profile-header">
        <img 
          src={user.avatar} 
          alt={`${user.name}'s avatar`} 
          className="avatar"
        />
        <h2>{user.name}</h2>
        <button 
          onClick={toggleTheme} 
          className="theme-toggle"
        >
          {currentTheme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>
      
      <div className="profile-details">
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Role:</strong> {user.role}</p>
        
        <button 
          onClick={toggleExpand}
          className={`expand-button theme-${currentTheme}`}
        >
          {isExpanded ? 'Show Less' : 'Show More'}
        </button>
        
        {isExpanded && (
          <div className="additional-info">
            <p><strong>Joined:</strong> {user.joinDate}</p>
            <p><strong>Last Active:</strong> {user.lastActive}</p>
            <p><strong>Bio:</strong> {user.bio}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserProfile;
