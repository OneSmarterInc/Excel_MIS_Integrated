import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { readError } from '../../api/client';
import { Button, Choice, Field, Notice } from '../../components/ui';
import { useAuth } from '../../store/auth';
import { colors, mono, spacing, type } from '../../theme';

function Shell({ children, heading, sub }) {
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ flex: 1, backgroundColor: colors.canvas }}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.masthead}>
          <Text style={styles.mark}>X</Text>
          <View style={{ flex: 1 }}>
            <Text style={styles.course}>MIS 3000</Text>
            <Text style={styles.tagline}>Excel Fundamentals for Business</Text>
          </View>
        </View>
        <View style={styles.card}>
          <Text style={type.title}>{heading}</Text>
          <Text style={[type.small, { marginTop: 4, marginBottom: spacing(2) }]}>{sub}</Text>
          {children}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export function LoginScreen({ navigation }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('STUDENT');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password, role);
    } catch (err) {
      setError(readError(err, 'Email or password is incorrect.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell heading="Sign in" sub="Use the account your department set up for this course.">
      <Choice
        value={role}
        onChange={setRole}
        options={[
          { value: 'STUDENT', label: 'Student' },
          { value: 'FACULTY', label: 'Faculty' },
          { value: 'ADMIN', label: 'Admin' },
        ]}
      />
      <Notice text={error} tone="error" />
      <Field
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="you@university.edu"
      />
      <Field
        label="Password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        placeholder="Your password"
      />
      <Button label={busy ? 'Signing in' : 'Sign in'} onPress={submit} disabled={busy} />
      <Pressable onPress={() => navigation.navigate('Register')} style={styles.link}>
        <Text style={styles.linkText}>Create an account</Text>
      </Pressable>
      <View style={styles.demo}>
        <Text style={styles.demoLine}>faculty@mis3000.edu / faculty123</Text>
        <Text style={styles.demoLine}>student@mis3000.edu / student123</Text>
        <Text style={styles.demoLine}>admin@mis3000.edu / admin123</Text>
      </View>
    </Shell>
  );
}

export function RegisterScreen({ navigation }) {
  const { register } = useAuth();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [role, setRole] = useState('STUDENT');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const update = (key) => (value) => setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await register(form.name.trim(), form.email.trim(), form.password, role);
    } catch (err) {
      setError(readError(err, 'That account could not be created.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell heading="Create an account" sub="Students join courses with a course code afterwards.">
      <Choice
        value={role}
        onChange={setRole}
        options={[
          { value: 'STUDENT', label: 'Student' },
          { value: 'FACULTY', label: 'Faculty' },
          { value: 'ADMIN', label: 'Admin' },
        ]}
      />
      <Notice text={error} tone="error" />
      <Field label="Full name" value={form.name} onChangeText={update('name')} placeholder="Asha Patel" />
      <Field
        label="Email"
        value={form.email}
        onChangeText={update('email')}
        autoCapitalize="none"
        keyboardType="email-address"
        placeholder="you@university.edu"
      />
      <Field
        label="Password"
        value={form.password}
        onChangeText={update('password')}
        secureTextEntry
        hint="At least six characters."
      />
      <Button label={busy ? 'Creating' : 'Create account'} onPress={submit} disabled={busy} />
      <Pressable onPress={() => navigation.goBack()} style={styles.link}>
        <Text style={styles.linkText}>Back to sign in</Text>
      </Pressable>
    </Shell>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: spacing(2.5), paddingTop: spacing(7), maxWidth: 520, width: '100%', alignSelf: 'center' },
  masthead: { flexDirection: 'row', alignItems: 'center', marginBottom: spacing(3) },
  mark: {
    fontSize: 17,
    fontWeight: '700',
    color: colors.paper,
    backgroundColor: colors.accent,
    borderRadius: 9,
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginRight: 12,
    overflow: 'hidden',
  },
  course: { fontSize: 20, fontWeight: '700', color: colors.ink, letterSpacing: -0.3 },
  tagline: { fontSize: 13, color: colors.muted },
  card: {
    backgroundColor: colors.paper,
    borderWidth: 1,
    borderColor: colors.grid,
    borderRadius: 14,
    padding: spacing(3),
  },
  link: { paddingVertical: spacing(1.5), alignItems: 'center' },
  linkText: { color: colors.accent, fontWeight: '600', fontSize: 14 },
  demo: { borderTopWidth: 1, borderTopColor: colors.grid, paddingTop: spacing(1.5) },
  demoLine: { fontFamily: mono, fontSize: 12, color: colors.muted, marginBottom: 2 },
});
