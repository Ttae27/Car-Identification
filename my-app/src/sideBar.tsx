import React from "react";

interface SidebarProps {
  currentView: string;
  onNavigate: (view: 'list' | 'settings') => void;
}

const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo"></div>

      <div className="sidebar-nav-links">
        <div 
          className={`sidebar-menu ${currentView === 'list' ? 'active' : ''}`}
          onClick={() => onNavigate('list')}
        >
          <span className="sidebar-menu-text">แสดงรายการข้อมูล</span>
          <div className="sidebar-menu-badge"></div>
        </div>

        <div 
          className={`sidebar-menu ${currentView === 'settings' ? 'active' : ''}`}
          style={{ cursor: 'not-allowed' }}
        >
          <span className="sidebar-menu-text">ตั้งค่าระบบ</span>
          <div className="sidebar-menu-badge"></div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;