import React, { useState, useEffect } from 'react';
import './UserProfile.css';

const UserProfile = ({ user }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [screenSize, setScreenSize] = useState('desktop');

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 576) {
        setScreenSize('mobile');
      } else if (window.innerWidth < 992) {
        setScreenSize('tablet');
      } else {
        setScreenSize('desktop');
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initial check
    
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const responsiveClass = `user-profile responsive-${screenSize}`;

  return (
    <div className={responsiveClass}>
      <div className="profile-header">
        <img 
          src={user.avatar} 
          alt={`${user.name}'s avatar`} 
          className={`avatar avatar-${screenSize}`}
        />
        <h2 className={`name-${screenSize}`}>{user.name}</h2>
      </div>
      
      <div className="profile-details">
        <div className="contact-info">
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Role:</strong> {user.role}</p>
        </div>
        
        <button 
          onClick={toggleExpand}
          className="action-button"
        >
          {isExpanded ? 'Show Less' : 'Show More'}
        </button>
        
        {isExpanded && (
          <div className="additional-info">
            <p><strong>Joined:</strong> {user.joinDate}</p>
            <p><strong>Last Active:</strong> {user.lastActive}</p>
            {screenSize !== 'mobile' && (
              <p><strong>Bio:</strong> {user.bio}</p>
            )}
            {screenSize === 'mobile' && (
              <button className="action-button secondary" onClick={() => alert(user.bio)}>
                View Bio
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserProfile;
