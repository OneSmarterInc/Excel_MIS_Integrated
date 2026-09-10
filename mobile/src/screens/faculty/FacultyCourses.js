import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Field, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function FacultyCourses({ navigation }) {
  const [courses, setCourses] = useState(null);
  const [form, setForm] = useState({ code: '', name: '', description: '' });
  const [creating, setCreating] = useState(false);
  // Asked before the form: a course built from a book takes a different path from one
  // built out of slides, a montage or a list of topics.
  const [asking, setAsking] = useState(false);
  const [hasContent, setHasContent] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/courses/');
      setCourses(data);
      setError('');
    } catch (err) {
      setError(readError(err));
      setCourses([]);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const update = (key) => (value) => setForm((prev) => ({ ...prev, [key]: value }));

  const create = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const { data } = await api.post('/courses/', {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        description: form.description.trim(),
      });
      setForm({ code: '', name: '', description: '' });
      setCreating(false);
      load();
      navigation.navigate('FacultyCourseDetail', {
        id: data.id,
        code: data.code,
        openPanel: hasContent ? 'upload' : 'generate',
      });
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!courses) return <Loading label="Loading courses" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Course</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Create a course, then upload the book you teach from and let the app split it into
        chapters and modules.
      </Text>

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      {asking ? (
        <Surface>
          <Text style={type.heading}>Do you already have the content?</Text>
          <Text style={[type.small, { marginTop: 6, marginBottom: spacing(2) }]}>
            A book, a handout or a set of notes counts as content. Lecture slides, a montage of
            screens or a list of topic names do not, and the platform will write the book from
            those instead.
          </Text>
          <Button
            label="Yes, I have a book to upload"
            onPress={() => {
              setHasContent(true);
              setAsking(false);
              setCreating(true);
            }}
          />
          <Button
            tone="accent"
            label="No, build it from my slides or topics"
            onPress={() => {
              setHasContent(false);
              setAsking(false);
              setCreating(true);
            }}
            style={{ marginTop: 8 }}
          />
          <Button tone="quiet" label="Cancel" onPress={() => setAsking(false)} style={{ marginTop: 8 }} />
        </Surface>
      ) : null}

      {creating ? (
        <Surface>
          <Text style={styles.pathTag}>
            {hasContent
              ? 'You will upload a book after this step.'
              : 'You will upload slides, images or topics and the book gets written for you.'}
          </Text>
          <Field
            label="Course code"
            value={form.code}
            onChangeText={update('code')}
            autoCapitalize="characters"
            placeholder="MIS3000"
            hint="This is what students type to join."
          />
          <Field
            label="Course name"
            value={form.name}
            onChangeText={update('name')}
            placeholder="Excel Fundamentals for Business"
          />
          <Field
            label="Description"
            value={form.description}
            onChangeText={update('description')}
            multiline
            placeholder="What this course covers"
          />
          <Button
            label={busy ? 'Creating' : hasContent ? 'Create and upload the book' : 'Create and build the book'}
            onPress={create}
            disabled={busy}
          />
          <Button
            tone="quiet"
            label="Back"
            onPress={() => {
              setCreating(false);
              setAsking(true);
            }}
            style={{ marginTop: 8 }}
          />
        </Surface>
      ) : (
        <Button label="Create a course" onPress={() => setAsking(true)} style={{ marginBottom: spacing(2) }} />
      )}

      {courses.length === 0 ? (
        <Empty
          title="Nothing here yet"
          body="Your first course takes a code, a name and a book. The book is what the chapters, modules and quizzes are built from."
        />
      ) : (
        courses.map((course) => (
          <Pressable
            key={course.id}
            onPress={() => navigation.navigate('FacultyCourseDetail', { id: course.id, code: course.code })}
          >
            <Surface>
              <View style={styles.row}>
                <Text style={styles.code}>{course.code}</Text>
                <Text style={styles.open}>Open</Text>
              </View>
              <Text style={styles.name}>{course.name}</Text>
              {course.description ? (
                <Text style={[type.small, { marginTop: 4 }]} numberOfLines={2}>
                  {course.description}
                </Text>
              ) : null}
              <Text style={styles.meta}>
                {course.student_count} enrolled  ·  {course.book_count} book
                {course.book_count === 1 ? '' : 's'}
              </Text>
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
  meta: { fontSize: 13, color: colors.muted, marginTop: 8 },
  pathTag: {
    fontSize: 12.5,
    color: colors.accent,
    backgroundColor: colors.accentSoft,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: spacing(2),
  },
});
