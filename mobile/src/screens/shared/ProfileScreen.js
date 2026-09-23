import React, { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { API_HOST, readError } from '../../api/client';
import { Button, Field, Notice, Surface } from '../../components/ui';
import { useAuth } from '../../store/auth';
import { colors, mono, spacing, type } from '../../theme';

export default function ProfileScreen() {
  const { user, signOut, refreshProfile } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [ai, setAi] = useState(null);

  useEffect(() => {
    api
      .get('/ai-status/')
      .then(({ data }) => setAi(data))
      .catch(() => setAi(null));
  }, []);

  const save = async () => {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      await api.patch('/auth/profile/', { name: name.trim() });
      await refreshProfile();
      setMessage('Profile updated.');
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Profile</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Signed in as {user?.role === 'FACULTY' ? 'faculty' : 'a student'}.
      </Text>

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <Surface>
        <Field label="Name" value={name} onChangeText={setName} />
        <View style={styles.readOnly}>
          <Text style={styles.readOnlyLabel}>Email</Text>
          <Text style={styles.readOnlyValue}>{user?.email}</Text>
        </View>
        <View style={styles.readOnly}>
          <Text style={styles.readOnlyLabel}>Role</Text>
          <Text style={styles.readOnlyValue}>{user?.role}</Text>
        </View>
        <Button label={busy ? 'Saving' : 'Save changes'} onPress={save} disabled={busy} />
      </Surface>

      <Surface>
        <Text style={type.heading}>Explanations</Text>
        <Text style={[type.body, { marginTop: 6, color: colors.inkSoft }]}>
          Chapter and module explanations are written on this machine by Ollama. When Ollama is
          not running the app uses its own writer instead, so nothing breaks.
        </Text>
        <Text style={[styles.host, { color: ai?.running ? colors.accent : colors.amber }]}>
          {ai ? `${ai.writer}: ${ai.message}` : 'Checking the local model'}
        </Text>
      </Surface>

      <Surface>
        <Text style={type.heading}>Connection</Text>
        <Text style={[type.body, { marginTop: 6, color: colors.inkSoft }]}>
          This app is talking to the Django server below. Change it in src/api/client.js when you
          move to a phone on the same network as your laptop.
        </Text>
        <Text style={styles.host}>{API_HOST}</Text>
      </Surface>

      <Button label="Sign out" tone="danger" onPress={signOut} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    padding: spacing(2.5),
    paddingBottom: spacing(6),
    width: '100%',
    maxWidth: 1140,
    alignSelf: 'center',
  },
  readOnly: { marginBottom: spacing(2) },
  readOnlyLabel: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 4 },
  readOnlyValue: { fontFamily: mono, fontSize: 14, color: colors.ink },
  host: { fontFamily: mono, fontSize: 13, color: colors.accent, marginTop: 8 },
});
