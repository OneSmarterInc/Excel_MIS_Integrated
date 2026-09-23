import { Picker } from '@react-native-picker/picker';
import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Field, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

function Accuracy({ value }) {
  const tone = value >= 75 ? colors.accent : value >= 50 ? colors.amber : colors.red;
  return (
    <View style={styles.track}>
      <View style={[styles.fill, { width: `${Math.max(3, value)}%`, backgroundColor: tone }]} />
    </View>
  );
}

export default function FeedbackScreen() {
  const [courses, setCourses] = useState(null);
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [comment, setComment] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadCourses = useCallback(async () => {
    try {
      const { data: mine } = await api.get('/courses/');
      setCourses(mine);
      setSelected((prev) => prev ?? mine[0]?.id ?? null);
    } catch (err) {
      setError(readError(err));
      setCourses([]);
    }
  }, []);

  const loadFeedback = useCallback(async (courseId) => {
    if (!courseId) return;
    try {
      const { data: payload } = await api.get(`/feedback/course/${courseId}/`);
      setData(payload);
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
    loadFeedback(selected);
  }, [selected, loadFeedback]);

  const send = async () => {
    if (!comment.trim() || !selected) return;
    setBusy(true);
    setMessage('');
    try {
      await api.post('/feedback/', { course: selected, rating: 5, comment: comment.trim() });
      setComment('');
      setMessage('Thanks. Your instructor can see this against the course.');
      loadFeedback(selected);
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!courses) return <Loading label="Loading feedback" />;

  if (courses.length === 0) {
    return (
      <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
        <Text style={type.title}>Feedback</Text>
        <Empty
          title="Join a course first"
          body="Feedback is built from the quizzes you take, so it appears once you have joined a course and answered a set of questions."
        />
      </ScrollView>
    );
  }

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Feedback</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        What your quiz answers say about each course, section by section.
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

      {data ? (
        <>
          <Surface>
            <Text style={styles.big}>{data.overall_percentage}%</Text>
            <Text style={styles.marks}>Marks {data.marks}</Text>
            <Text style={styles.message}>{data.message}</Text>
          </Surface>

          {data.skills.length ? (
            <Surface>
              <Text style={type.heading}>Skill by skill</Text>
              {data.skills.map((skill) => (
                <View key={skill.skill} style={styles.skillRow}>
                  <View style={styles.skillHead}>
                    <Text style={styles.skillName}>{skill.skill}</Text>
                    <Text style={styles.skillScore}>
                      {skill.correct}/{skill.asked}
                    </Text>
                  </View>
                  <Accuracy value={skill.accuracy} />
                </View>
              ))}
            </Surface>
          ) : null}

          {data.sections.length ? (
            <Surface>
              <Text style={type.heading}>Quizzes you have taken</Text>
              {data.sections.map((section) => (
                <View key={section.attempt_id} style={styles.sectionRow}>
                  <Text style={styles.sectionLabel} numberOfLines={2}>{section.label}</Text>
                  <Text style={styles.sectionScore}>
                    {section.score}/{section.total}
                  </Text>
                </View>
              ))}
            </Surface>
          ) : null}

          <Surface>
            <Text style={type.heading}>Tell your instructor something</Text>
            <View style={{ height: 10 }} />
            <Field
              label="Your comment"
              value={comment}
              onChangeText={setComment}
              multiline
              placeholder="What helped, what did not"
            />
            <Button label={busy ? 'Sending' : 'Send feedback'} onPress={send} disabled={busy} />
            {data.comments.map((entry) => (
              <View key={entry.id} style={styles.comment}>
                <Text style={styles.commentText}>{entry.comment}</Text>
                {entry.faculty_reply ? (
                  <Text style={styles.reply}>Reply: {entry.faculty_reply}</Text>
                ) : null}
              </View>
            ))}
          </Surface>
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
  pickerFrame: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    backgroundColor: colors.paper,
    marginBottom: spacing(2),
  },
  big: { fontSize: 34, fontWeight: '700', color: colors.ink },
  marks: { fontFamily: mono, fontSize: 13, color: colors.muted, marginTop: 2 },
  message: { fontSize: 15, lineHeight: 23, color: colors.inkSoft, marginTop: 10 },
  skillRow: { marginTop: 12 },
  skillHead: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 5 },
  skillName: { fontSize: 14, color: colors.ink, flex: 1, paddingRight: 8 },
  skillScore: { fontFamily: mono, fontSize: 12, color: colors.muted },
  track: { height: 7, backgroundColor: colors.grid, borderRadius: 999, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 999 },
  sectionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 8,
  },
  sectionLabel: { flex: 1, fontSize: 14, color: colors.ink, paddingRight: 10 },
  sectionScore: { fontFamily: mono, fontSize: 13, color: colors.inkSoft },
  comment: { borderTopWidth: 1, borderTopColor: colors.grid, paddingTop: 10, marginTop: 12 },
  commentText: { fontSize: 14, color: colors.ink, lineHeight: 21 },
  reply: { fontSize: 13, color: colors.accent, marginTop: 6 },
});
