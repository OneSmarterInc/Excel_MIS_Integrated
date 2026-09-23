import { Picker } from '@react-native-picker/picker';
import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function StudentCourses({ navigation }) {
  const [codes, setCodes] = useState([]);
  const [joined, setJoined] = useState(null);
  const [selected, setSelected] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [available, mine] = await Promise.all([
        api.get('/course-codes/'),
        api.get('/courses/'),
      ]);
      setCodes(available.data);
      setJoined(mine.data);
      const first = available.data.find((c) => !c.joined);
      setSelected((prev) => prev || first?.code || available.data[0]?.code || '');
      setError('');
    } catch (err) {
      setError(readError(err));
      setJoined([]);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const join = async () => {
    if (!selected) return;
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const { data } = await api.post('/join-course/', { code: selected });
      setMessage(`You joined ${data.code}. Open it below to start reading.`);
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!joined) return <Loading label="Loading courses" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Course</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Course codes appear here once an instructor has opened a course to your email address.
        You can also accept them under Courses provided in the sidebar.
      </Text>

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <Surface>
        <Text style={styles.label}>Course code</Text>
        <View style={styles.pickerFrame}>
          <Picker
            selectedValue={selected}
            onValueChange={setSelected}
            style={styles.picker}
            dropdownIconColor={colors.ink}
          >
            {codes.length === 0 ? (
              <Picker.Item label="No course has been opened to you yet" value="" />
            ) : (
              codes.map((course) => (
                <Picker.Item
                  key={course.id}
                  label={`${course.code} — ${course.name}${course.joined ? ' (joined)' : ''}`}
                  value={course.code}
                />
              ))
            )}
          </Picker>
        </View>
        <Button
          tone="accent"
          label={busy ? 'Joining' : 'Join with this code'}
          onPress={join}
          disabled={busy || !selected}
        />
      </Surface>

      <Text style={[type.heading, { marginTop: spacing(1), marginBottom: spacing(1) }]}>
        Your courses
      </Text>

      {joined.length === 0 ? (
        <Empty
          title="Nothing joined yet"
          body="Open Courses provided in the sidebar to accept a course your instructor has given you. Everything they uploaded shows up here straight after."
        />
      ) : (
        joined.map((course) => (
          <Pressable
            key={course.id}
            onPress={() =>
              navigation.navigate('StudentCourseDetail', { id: course.id, code: course.code })
            }
          >
            <Surface>
              <View style={styles.row}>
                <Text style={styles.code}>{course.code}</Text>
                <Text style={styles.open}>Open</Text>
              </View>
              <Text style={styles.name}>{course.name}</Text>
              <Text style={styles.meta}>Taught by {course.faculty_name}</Text>
            </Surface>
          </Pressable>
        ))
      )}
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
  label: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  pickerFrame: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    marginBottom: spacing(2),
    backgroundColor: colors.paper,
  },
  picker: { color: colors.ink },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
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
  open: { color: colors.accent, fontWeight: '600', fontSize: 13 },
  name: { fontSize: 17, fontWeight: '600', color: colors.ink, marginTop: 10 },
  meta: { fontSize: 12, color: colors.muted, marginTop: 4 },
});
