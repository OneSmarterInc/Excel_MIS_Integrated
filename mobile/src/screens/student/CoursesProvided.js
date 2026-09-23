import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function CoursesProvided({ navigation }) {
  const [invitations, setInvitations] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/my-invitations/');
      setInvitations(data);
      setError('');
    } catch (err) {
      setError(readError(err));
      setInvitations([]);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const respond = async (invitation, decision) => {
    setBusy(invitation.id);
    setMessage('');
    try {
      await api.post(`/invitations/${invitation.id}/respond/`, { decision });
      setMessage(
        decision === 'accept'
          ? `${invitation.course_code} is open. Find it under Course in the sidebar.`
          : `${invitation.course_code} declined. You can accept it later if you change your mind.`
      );
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(null);
    }
  };

  if (!invitations) return <Loading label="Looking for courses given to you" />;

  const waiting = invitations.filter((item) => item.status === 'PENDING');
  const settled = invitations.filter((item) => item.status !== 'PENDING');

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Courses provided</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Courses your instructors have opened to your email address. Accept one and its chapters
        and quizzes appear under Course.
      </Text>

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      {invitations.length === 0 ? (
        <Empty
          title="Nothing yet"
          body="When an instructor gives your email address access to a course, it shows up here for you to accept."
        />
      ) : null}

      {waiting.map((invitation) => (
        <Surface key={invitation.id}>
          <View style={styles.head}>
            <Text style={styles.code}>{invitation.course_code}</Text>
            <Text style={styles.pending}>Waiting for you</Text>
          </View>
          <Text style={styles.name}>{invitation.course_name}</Text>
          <Text style={styles.meta}>Given to you by {invitation.faculty_name}</Text>
          <View style={styles.actions}>
            <Button
              tone="accent"
              label={busy === invitation.id ? 'Accepting' : 'Accept'}
              onPress={() => respond(invitation, 'accept')}
              disabled={busy === invitation.id}
              style={{ flex: 1, marginRight: 8 }}
            />
            <Button
              tone="quiet"
              label="Decline"
              onPress={() => respond(invitation, 'decline')}
              disabled={busy === invitation.id}
              style={{ flex: 1 }}
            />
          </View>
        </Surface>
      ))}

      {settled.length ? (
        <>
          <Text style={[type.heading, { marginTop: spacing(1), marginBottom: spacing(1) }]}>
            Already answered
          </Text>
          {settled.map((invitation) => (
            <Surface key={invitation.id}>
              <View style={styles.head}>
                <Text style={styles.code}>{invitation.course_code}</Text>
                <Text
                  style={[
                    styles.settled,
                    invitation.status === 'ACCEPTED'
                      ? { color: colors.accent }
                      : { color: colors.red },
                  ]}
                >
                  {invitation.status === 'ACCEPTED' ? 'Accepted' : 'Declined'}
                </Text>
              </View>
              <Text style={styles.name}>{invitation.course_name}</Text>
              {invitation.status === 'ACCEPTED' ? (
                <Button
                  tone="quiet"
                  label="Open it under Course"
                  onPress={() => navigation.navigate('Course')}
                  style={{ marginTop: spacing(1.5) }}
                />
              ) : (
                <Button
                  tone="quiet"
                  label="Accept after all"
                  onPress={() => respond(invitation, 'accept')}
                  style={{ marginTop: spacing(1.5) }}
                />
              )}
            </Surface>
          ))}
        </>
      ) : null}
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
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  code: {
    fontFamily: mono,
    fontSize: 12,
    color: colors.accent,
    backgroundColor: colors.accentSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    overflow: 'hidden',
  },
  pending: { fontSize: 12, fontWeight: '700', color: colors.amber },
  settled: { fontSize: 12, fontWeight: '700' },
  name: { fontSize: 17, fontWeight: '600', color: colors.ink, marginTop: 10 },
  meta: { fontSize: 12.5, color: colors.muted, marginTop: 4 },
  actions: { flexDirection: 'row', marginTop: spacing(2) },
});
