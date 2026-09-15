import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Empty, Loading, Notice, Stat, Surface } from '../../components/ui';
import { useAuth } from '../../store/auth';
import { colors, mono, spacing, type } from '../../theme';

export default function StudentDashboard({ navigation }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [summary, history] = await Promise.all([
        api.get('/student/dashboard/'),
        api.get('/quizzes/attempts/'),
      ]);
      setData(summary.data);
      setAttempts(history.data.filter((a) => a.submitted_at).slice(0, 6));
      setError('');
    } catch (err) {
      setError(readError(err));
    } finally {
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (!data && !error) return <Loading label="Loading your marks" />;

  return (
    <ScrollView
      style={{ backgroundColor: colors.canvas }}
      contentContainerStyle={styles.page}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />
      }
    >
      <Text style={type.title}>Dashboard</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Where you stand in each course, {user?.name}.
      </Text>

      <Notice text={error} tone="error" />

      {data ? (
        <>
          <View style={styles.statRow}>
            <Stat value={data.totals.courses} label="Courses joined" />
            <Stat value={data.totals.quizzes_taken} label="Quizzes taken" tone="good" />
            <Stat
              value={
                data.totals.average_percentage === null
                  ? '—'
                  : `${data.totals.average_percentage}%`
              }
              label={data.totals.marks ? `Average mark (${data.totals.marks})` : 'Average mark'}
              tone="warn"
            />
          </View>

          {data.courses.length === 0 ? (
            <Empty
              title="No courses joined"
              body="Open Course in the sidebar, pick your course code from the dropdown and join. Your chapters and quizzes appear straight after."
            />
          ) : (
            data.courses.map((course) => (
              <Surface key={course.course_id}>
                <View style={styles.head}>
                  <Text style={styles.code}>{course.code}</Text>
                  <Text style={styles.percent}>
                    {course.average_percentage === null ? '—' : `${course.average_percentage}%`}
                  </Text>
                </View>
                <Text style={styles.name}>{course.name}</Text>
                <Text style={styles.meta}>Taught by {course.faculty_name}</Text>
                <View style={styles.marksRow}>
                  {course.quizzes_taken ? (
                    <>
                      <Text style={styles.marks}>Marks {course.marks}</Text>
                      <Text style={styles.marks}>Best {course.best_percentage}%</Text>
                      <Text style={styles.marks}>
                        {course.quizzes_taken} {course.quizzes_taken === 1 ? 'quiz' : 'quizzes'}
                      </Text>
                    </>
                  ) : (
                    <Text style={styles.marks}>No quiz taken yet</Text>
                  )}
                </View>
              </Surface>
            ))
          )}

          {attempts.length ? (
            <Surface>
              <Text style={type.heading}>Recent quizzes</Text>
              {attempts.map((attempt) => (
                <View key={attempt.id} style={styles.attemptRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.attemptLabel} numberOfLines={1}>{attempt.label}</Text>
                    <Text style={styles.meta}>{attempt.course_code}</Text>
                  </View>
                  <Text style={styles.attemptScore}>
                    {attempt.score}/{attempt.total}
                  </Text>
                </View>
              ))}
            </Surface>
          ) : null}
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
  statRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1.5) },
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
  percent: { fontSize: 20, fontWeight: '700', color: colors.accent },
  name: { fontSize: 17, fontWeight: '600', color: colors.ink, marginTop: 10 },
  meta: { fontSize: 12, color: colors.muted, marginTop: 2 },
  marksRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 10 },
  marks: { fontFamily: mono, fontSize: 12, color: colors.inkSoft, marginRight: 14 },
  attemptRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 8,
  },
  attemptLabel: { fontSize: 14, color: colors.ink },
  attemptScore: { fontFamily: mono, fontSize: 14, color: colors.inkSoft },
});
