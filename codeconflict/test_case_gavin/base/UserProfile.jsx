import React, { useState } from 'react';
import './UserProfile.css';

const UserProfile = ({ user }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="user-profile">
      <div className="profile-header">
        <img 
          src={user.avatar} 
          alt={`${user.name}'s avatar`} 
          className="avatar"
        />
        <h2>{user.name}</h2>
      </div>
      
      <div className="profile-details">
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Role:</strong> {user.role}</p>
        
        <button onClick={toggleExpand}>
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
