import { useState, useEffect } from 'react';
import { Trophy, TrendingUp, BarChart3, PieChart as PieChartIcon, Zap, Code, Globe, Terminal, Ruler, Wrench, Image, ImagePlus, Mic, LayoutGrid, ChevronDown, Sun, Moon } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useLanguageStore } from '@/store/useLanguageStore';
import { useThemeStore } from '@/store/useThemeStore';

const sections = [
  { id: 'top-models', label: 'top_models', icon: TrendingUp },
  { id: 'leaderboard', label: 'leaderboard', icon: Trophy },
  { id: 'market-share', label: 'market_share', icon: PieChartIcon },
  { id: 'benchmarks', label: 'benchmarks', icon: BarChart3 },
  { id: 'fastest', label: 'fastest_models', icon: Zap },
  { id: 'categories', label: 'categories', icon: Code },
  { id: 'languages', label: 'languages', icon: Globe },
  { id: 'programming', label: 'programming', icon: Terminal },
  { id: 'context-length', label: 'context_length', icon: Ruler },
  { id: 'tool-calls', label: 'tool_calls', icon: Wrench },
  { id: 'images', label: 'images', icon: Image },
  { id: 'image-output', label: 'image_output', icon: ImagePlus },
  { id: 'audio-input', label: 'audio_input', icon: Mic },
  { id: 'top-apps', label: 'top_apps', icon: LayoutGrid },
];

export default function Navbar() {
  const { lang, setLang, t } = useLanguageStore();
  const { theme, toggleTheme } = useThemeStore();
  const [activeSection, setActiveSection] = useState('top-models');
  const [isNavOpen, setIsNavOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const isHome = location.pathname === '/';

  useEffect(() => {
    if (!isHome) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        }
      },
      { rootMargin: '-20% 0px -70% 0px' }
    );
    for (const s of sections) {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [isHome]);

  const handleNavClick = (sectionId: string) => {
    setIsNavOpen(false);
    if (isHome) {
      const el = document.getElementById(sectionId);
      el?.scrollIntoView({ behavior: 'smooth' });
    } else {
      navigate('/');
      setTimeout(() => {
        const el = document.getElementById(sectionId);
        el?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  const toggleLanguage = () => {
    setLang(lang === 'zh' ? 'en' : 'zh');
  };

  return (
    <>
      {/* 顶部Logo和语言/主题切换 */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-light-300 dark:border-dark-700 bg-light-50/80 dark:bg-dark-950/80 backdrop-blur-md">
        <div className="flex h-14 items-center justify-between px-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 transition-opacity hover:opacity-80"
          >
            <Trophy className="h-5 w-5 text-accent" />
            <span className="font-heading text-lg font-bold text-gray-900 dark:text-white">
              AI Rankings
            </span>
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-zinc-500 hover:bg-light-200 dark:hover:bg-dark-700 hover:text-gray-700 dark:hover:text-zinc-300 transition-colors"
            >
              {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
              <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>

            <button
              onClick={toggleLanguage}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-zinc-500 hover:bg-light-200 dark:hover:bg-dark-700 hover:text-gray-700 dark:hover:text-zinc-300 transition-colors"
            >
              <Globe className="h-3.5 w-3.5" />
              <span>{lang === 'zh' ? 'EN' : '中文'}</span>
            </button>
            
            <button
              onClick={() => setIsNavOpen(!isNavOpen)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-zinc-500 hover:bg-light-200 dark:hover:bg-dark-700 hover:text-gray-700 dark:hover:text-zinc-300 transition-colors"
            >
              <span>{t('categories')}</span>
              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isNavOpen ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
      </nav>

      {/* 右侧浮动导航菜单 */}
      <div
        className={`fixed top-14 right-0 z-40 transition-all duration-300 ${
          isNavOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="w-56 rounded-l-lg border border-light-300 dark:border-dark-700 border-r-0 bg-white/95 dark:bg-dark-900/95 backdrop-blur-md shadow-xl overflow-hidden">
          <div className="max-h-[calc(100vh-8rem)] overflow-y-auto py-2">
            {sections.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent/10 text-accent-light'
                      : 'text-gray-500 dark:text-zinc-400 hover:bg-light-200 dark:hover:bg-dark-700 hover:text-gray-700 dark:hover:text-zinc-200'
                  }`}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  <span>{t(item.label)}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 点击其他区域关闭导航 */}
      {isNavOpen && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setIsNavOpen(false)}
        />
      )}
    </>
  );
}
