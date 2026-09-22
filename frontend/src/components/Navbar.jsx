import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import {
  Shield,
  LayoutDashboard,
  ScanSearch,
  Link2,
  Settings,
  LogOut,
  Plus,
} from 'lucide-react';

export default function Navbar() {
  const { user, signOut, isAuthenticated } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', Icon: LayoutDashboard },
    { to: '/scan/new', label: 'Scan', Icon: ScanSearch },
    { to: '/connections', label: 'Connections', Icon: Link2 },
    { to: '/settings/agent', label: 'Agent', Icon: Settings },
  ];

  function isActive(path) {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  }

  return (
    <nav
      className="sticky top-0 z-50 flex items-center justify-between px-6 py-3"
      style={{
        backgroundColor: 'var(--color-bg)',
        borderBottom: '1px solid var(--color-border)',
        backdropFilter: 'blur(12px)',
      }}
    >
      {/* Logo */}
      <Link to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-2.5 no-underline">
        <div
          className="flex items-center justify-center rounded-lg"
          style={{
            width: 32, height: 32,
            backgroundColor: 'var(--color-accent-dim)',
          }}
        >
          <Shield size={18} style={{ color: 'var(--color-accent)' }} />
        </div>
        <span className="font-mono font-bold text-sm tracking-wider" style={{ color: 'var(--color-text-primary)' }}>
          PHISH<span style={{ color: 'var(--color-accent)' }}>GUARD</span>
        </span>
      </Link>

      {/* Nav Links */}
      {isAuthenticated && (
        <div className="flex items-center gap-1">
          {navLinks.map(({ to, label, Icon }) => (
            <Link
              key={to}
              to={to}
              className="nav-link"
              aria-current={isActive(to) ? 'page' : undefined}
            >
              <Icon size={14} />
              {label}
            </Link>
          ))}
        </div>
      )}

      {/* Right actions */}
      <div className="flex items-center gap-3">
        {isAuthenticated && (
          <>
            {!isActive('/scan/new') && (
              <button
                className="btn-primary"
                style={{ padding: '6px 14px', fontSize: '11px' }}
                onClick={() => navigate('/scan/new')}
              >
                <Plus size={13} />
                New Scan
              </button>
            )}

            <button
              onClick={signOut}
              className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-mono cursor-pointer border-none bg-transparent transition-colors"
              style={{ color: 'var(--color-text-muted)' }}
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
