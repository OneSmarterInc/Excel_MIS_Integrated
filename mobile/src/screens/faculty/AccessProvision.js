import { Picker } from '@react-native-picker/picker';
import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

const STATUS_TONE = {
  ACCEPTED: { label: 'Accepted', color: colors.accent, background: colors.accentSoft },
  PENDING: { label: 'Waiting', color: colors.amber, background: colors.amberSoft },
  DECLINED: { label: 'Declined', color: colors.red, background: colors.redSoft },
};

export default function AccessProvision() {
  const [courses, setCourses] = useState(null);
  const [selected, setSelected] = useState(null);
  const [invitations, setInvitations] = useState([]);
  const [emails, setEmails] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadCourses = useCallback(async () => {
    try {
      const { data } = await api.get('/courses/');
      setCourses(data);
      setSelected((prev) => prev ?? data[0]?.id ?? null);
    } catch (err) {
      setError(readError(err));
      setCourses([]);
    }
  }, []);

  const loadInvitations = useCallback(async (courseId) => {
    if (!courseId) return;
    try {
      const { data } = await api.get(`/courses/${courseId}/invitations/`);
      setInvitations(data);
      setError('');
    } catch (err) {
      setError(readError(err));
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadCourses();
    }, [loadCourses])
  );

  useEffect(() => {
    loadInvitations(selected);
  }, [selected, loadInvitations]);

  const give = async () => {
    if (!emails.trim() || !selected) return;
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const { data } = await api.post(`/courses/${selected}/invitations/`, { emails });
      setInvitations(data.invitations);
      setEmails('');
      const parts = [];
      if (data.added.length) parts.push(`${data.added.length} added`);
      if (data.already_invited.length) parts.push(`${data.already_invited.length} already had access`);
      if (data.not_an_email.length) parts.push(`${data.not_an_email.join(', ')} is not an email address`);
      setMessage(parts.join('. ') || 'Nothing to add.');
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (invitationId) => {
    try {
      await api.delete(`/invitations/${invitationId}/`);
      setMessage('Access removed. That student can no longer open the course.');
      loadInvitations(selected);
    } catch (err) {
      setError(readError(err));
    }
  };

  if (!courses) return <Loading label="Loading your courses" />;

  if (courses.length === 0) {
    return (
      <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
        <Text style={type.title}>Access provision</Text>
        <Empty
          title="Create a course first"
          body="Once a course exists you can name the students who may take it, and the course opens for them as soon as they accept."
        />
      </ScrollView>
    );
  }

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Access provision</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Name the students who may take a course. It appears under Courses provided in their app,
        and the course opens for them once they accept.
      </Text>

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <View style={styles.pickerFrame}>
        <Picker selectedValue={selected} onValueChange={setSelected} style={{ color: colors.ink }}>
          {courses.map((course) => (
            <Picker.Item key={course.id} label={`${course.code} — ${course.name}`} value={course.id} />
          ))}
        </Picker>
      </View>

      <Surface>
        <Text style={styles.label}>Student email addresses</Text>
        <TextInput
          value={emails}
          onChangeText={setEmails}
          multiline
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          placeholder={'asha@wright.edu\nram@wright.edu, priya@wright.edu'}
          placeholderTextColor={colors.muted}
          style={styles.input}
        />
        <Text style={[type.small, { marginBottom: spacing(1.5) }]}>
          One per line, or separated by commas. An address can be added before the student has
          made an account.
        </Text>
        <Button
          tone="accent"
          label={busy ? 'Giving access' : 'Give access'}
          onPress={give}
          disabled={busy || !emails.trim()}
        />
      </Surface>

      <Surface>
        <Text style={type.heading}>Who has access</Text>
        {invitations.length === 0 ? (
          <Text style={[type.small, { marginTop: 6 }]}>
            Nobody yet. Add an email address above.
          </Text>
        ) : (
          invitations.map((invitation) => {
            const tone = STATUS_TONE[invitation.status] || STATUS_TONE.PENDING;
            return (
              <View key={invitation.id} style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.email} numberOfLines={1}>{invitation.email}</Text>
                  {invitation.student_name ? (
                    <Text style={styles.meta}>{invitation.student_name}</Text>
                  ) : (
                    <Text style={styles.meta}>No account under this address yet</Text>
                  )}
                </View>
                <Text
                  style={[styles.status, { color: tone.color, backgroundColor: tone.background }]}
                >
                  {tone.label}
                </Text>
                <Pressable onPress={() => revoke(invitation.id)}>
                  <Text style={styles.revoke}>Remove</Text>
                </Pressable>
              </View>
            );
          })
        )}
      </Surface>
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
  pickerFrame: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    backgroundColor: colors.paper,
    marginBottom: spacing(2),
  },
  label: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    minHeight: 84,
    padding: 10,
    fontFamily: mono,
    fontSize: 13,
    color: colors.ink,
    textAlignVertical: 'top',
    marginBottom: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    paddingVertical: 10,
    marginTop: 8,
  },
  email: { fontFamily: mono, fontSize: 13, color: colors.ink },
  meta: { fontSize: 12, color: colors.muted, marginTop: 2 },
  status: {
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginHorizontal: 10,
  },
  revoke: { color: colors.red, fontSize: 12.5, fontWeight: '600' },
});
