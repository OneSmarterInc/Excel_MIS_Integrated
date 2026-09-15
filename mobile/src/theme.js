// The house style: a deep green sidebar, a pale grey page, white rounded cards and one
// green accent for anything a person can act on. Monospace stays for formulas and cell
// values, since those read as spreadsheet content wherever they appear.
import { Platform } from 'react-native';

export const colors = {
  ink: '#16202A',
  inkSoft: '#465A6B',
  paper: '#FFFFFF',
  canvas: '#F4F6F7',
  grid: '#E4E9EC',
  gridStrong: '#CBD4D9',
  accent: '#157347',
  accentDark: '#0F5A36',
  accentSoft: '#E7F2EC',
  amber: '#B26B12',
  amberSoft: '#FDF2E1',
  red: '#B23B3B',
  redSoft: '#FBE9E9',
  muted: '#6B7A85',

  // The sidebar and the segmented tabs have their own colours in this theme.
  sidebar: '#12402D',
  sidebarLine: '#1E5540',
  sidebarText: '#C9DCD2',
  tabActive: '#EDE3F7',
  tabActiveText: '#4B2E70',
};

export const radius = { card: 12, control: 10, pill: 999 };

export const shadow = {
  shadowColor: '#0B1F17',
  shadowOpacity: 0.05,
  shadowRadius: 10,
  shadowOffset: { width: 0, height: 2 },
  elevation: 1,
};

export const mono = Platform.select({
  ios: 'Menlo',
  android: 'monospace',
  default: 'ui-monospace, SFMono-Regular, Menlo, monospace',
});

export const type = {
  title: { fontSize: 26, fontWeight: '700', color: colors.ink, letterSpacing: -0.5 },
  heading: { fontSize: 18, fontWeight: '700', color: colors.ink },
  body: { fontSize: 15, lineHeight: 23, color: colors.ink },
  small: { fontSize: 13, color: colors.muted },
  cell: { fontFamily: mono, fontSize: 13, color: colors.ink },
};

export const spacing = (n) => n * 8;
