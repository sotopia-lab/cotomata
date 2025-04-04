import React, { useState, useEffect } from 'react';
import './UserProfile.css';

const UserProfile = ({ user, theme = 'light' }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(theme);
  const [screenSize, setScreenSize] = useState('desktop');

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  const toggleTheme = () => {
    setCurrentTheme(currentTheme === 'light' ? 'dark' : 'light');
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

  const composedClass = `user-profile theme-${currentTheme} responsive-${screenSize}`;

  return (
    <div className={composedClass}>
      <div className="profile-header">
        <img 
          src={user.avatar} 
          alt={`${user.name}'s avatar`} 
          className={`avatar avatar-${screenSize}`}
        />
        <h2 className={`name-${screenSize}`}>{user.name}</h2>
        <button 
          onClick={toggleTheme} 
          className="theme-toggle"
        >
          {currentTheme === 'light' ? '🌙' : '☀️'}
        </button>
      </div>
      
      <div className="profile-details">
        <div className="contact-info">
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Role:</strong> {user.role}</p>
        </div>
        
        <button 
          onClick={toggleExpand}
          className={`action-button theme-${currentTheme}`}
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
              <button className={`action-button secondary theme-${currentTheme}`} onClick={() => alert(user.bio)}>
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
