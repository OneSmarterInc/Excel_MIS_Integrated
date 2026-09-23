import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { Platform } from 'react-native';

// Android emulators reach the host machine on 10.0.2.2. A real phone needs the
// laptop's LAN address, so change LAN_ADDRESS once here and every screen follows.
const LAN_ADDRESS = 'http://192.168.1.10:8000';

export const API_HOST =
  Platform.OS === 'android'
    ? 'http://10.0.2.2:8000'
    : Platform.OS === 'web'
    ? 'http://127.0.0.1:8000'
    : LAN_ADDRESS;

const api = axios.create({ baseURL: `${API_HOST}/api`, timeout: 60000 });

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function readError(error, fallback = 'Something went wrong. Try again.') {
  const response = error?.response;
  const data = response?.data;

  // Django's debug pages come back as HTML. Dumping that into the app is useless, so say
  // what actually happened instead: almost always an old server still running.
  if (typeof data === 'string' && data.trimStart().startsWith('<')) {
    if (response.status === 404) {
      return `The server has no ${error?.config?.url || 'endpoint'} route. It is probably `
        + 'running older code, so stop it and start it again from the new backend folder.';
    }
    return `The server returned an error page (${response.status}). Check the terminal `
      + 'running Django for the traceback.';
  }
  const status = error?.response?.status;
  // Django's debug pages come back as a wall of HTML. Showing that to a person is useless,
  // so say what actually happened instead.
  if (typeof data === 'string' && data.trimStart().startsWith('<')) {
    if (status === 404) {
      return `The server does not have this endpoint (${error?.config?.url}). It is probably running an older copy of the backend, so stop it and start it again from the new folder.`;
    }
    return `The server returned an error page (HTTP ${status}). Check the terminal running Django.`;
  }
  if (!data) {
    return error?.message === 'Network Error'
      ? `Cannot reach the server at ${API_HOST}. Start the Django server, then check the address in src/api/client.js.`
      : fallback;
  }
  if (typeof data === 'string') return data;
  if (data.detail) return data.detail;
  const first = Object.values(data)[0];
  return Array.isArray(first) ? first[0] : String(first);
}

/**
 * Pull a generated document off the API and actually save it.
 *
 * The browser gets a real file download through a blob. A phone writes it into the app's
 * document folder when expo-file-system is installed, and otherwise reports the size so
 * the caller can say something useful rather than pretending it saved.
 */
export async function downloadDocument(path, filename) {
  const token = await AsyncStorage.getItem('access');
  const response = await fetch(`${API_HOST}/api${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(
      response.status === 403
        ? 'Nothing has been published for this book yet.'
        : `The server refused the download (${response.status}).`
    );
  }
  const blob = await response.blob();

  if (Platform.OS === 'web') {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    return { saved: filename, size: blob.size };
  }

  try {
    // eslint-disable-next-line global-require
    const FileSystem = require('expo-file-system');
    const uri = `${FileSystem.documentDirectory}${filename}`;
    const fr = new FileReader();
    const base64 = await new Promise((resolve, reject) => {
      fr.onload = () => {
        const res = String(fr.result || '');
        resolve(res.includes(',') ? res.split(',')[1] : res);
      };
      fr.onerror = reject;
      fr.readAsDataURL(blob);
    });
    await FileSystem.writeAsStringAsync(uri, base64, {
      encoding: FileSystem.EncodingType?.Base64 || 'base64',
    });
    return { saved: uri, size: blob.size };
  } catch (error) {
    return { saved: '', size: blob.size };
  }
}

export default api;
