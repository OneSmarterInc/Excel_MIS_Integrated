import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Empty, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function StudentCourseDetail({ route, navigation }) {
  const { id, code } = route.params;
  const [course, setCourse] = useState(null);
  const [open, setOpen] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/courses/${id}/`);
      setCourse(data);
      const firstChapter = data.books?.[0]?.chapters?.[0]?.id ?? null;
      setOpen((prev) => prev ?? firstChapter);
      setError('');
    } catch (err) {
      setError(readError(err));
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      navigation.setOptions({ title: code });
      load();
    }, [load, navigation, code])
  );

  if (!course) return <Loading label="Loading chapters" />;

  const books = course.books || [];

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>{course.name}</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Tap a chapter or a module to read the easy explanation, then take its quiz.
      </Text>

      <Notice text={error} tone="error" />

      {books.length === 0 ? (
        <Empty
          title="No material yet"
          body="Your instructor has not uploaded the book for this course. Check back after the next class."
        />
      ) : (
        books.map((book) => (
          <Surface key={book.id}>
            <Text style={styles.bookTitle}>{book.title}</Text>
            <Text style={styles.meta}>
              {book.chapter_count} chapters  ·  {book.module_count} modules
            </Text>

            {book.chapters.map((chapter) => {
              const expanded = open === chapter.id;
              return (
                <View key={chapter.id} style={styles.chapterBlock}>
                  <Pressable
                    style={styles.chapterRow}
                    onPress={() => setOpen(expanded ? null : chapter.id)}
                  >
                    <Text style={styles.chapterNumber}>{chapter.number}</Text>
                    <Text style={styles.chapterTitle} numberOfLines={2}>{chapter.title}</Text>
                    <Text style={styles.caret}>{expanded ? '\u2013' : '+'}</Text>
                  </Pressable>

                  {expanded ? (
                    <View style={styles.body}>
                      <View style={styles.actionRow}>
                        <Pressable
                          onPress={() =>
                            navigation.navigate('Content', {
                              kind: 'chapter',
                              id: chapter.id,
                              title: chapter.title,
                            })
                          }
                        >
                          <Text style={styles.action}>Read chapter</Text>
                        </Pressable>
                        <Pressable
                          onPress={() =>
                            navigation.navigate('Quiz', {
                              kind: 'chapter',
                              id: chapter.id,
                              title: chapter.title,
                            })
                          }
                        >
                          <Text style={styles.actionStrong}>Chapter quiz</Text>
                        </Pressable>
                      </View>

                      {chapter.modules.map((module) => (
                        <View key={module.id} style={styles.moduleRow}>
                          <Text style={styles.moduleNumber}>
                            {chapter.number}.{module.number}
                          </Text>
                          <View style={{ flex: 1 }}>
                            <Pressable
                              onPress={() =>
                                navigation.navigate('Content', {
                                  kind: 'module',
                                  id: module.id,
                                  title: module.title,
                                })
                              }
                            >
                              <Text style={styles.moduleTitle}>{module.title}</Text>
                            </Pressable>
                            <Pressable
                              onPress={() =>
                                navigation.navigate('Quiz', {
                                  kind: 'module',
                                  id: module.id,
                                  title: module.title,
                                })
                              }
                            >
                              <Text style={styles.moduleQuiz}>Take the module quiz</Text>
                            </Pressable>
                          </View>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              );
            })}

          </Surface>
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
  bookTitle: { fontSize: 16, fontWeight: '700', color: colors.ink },
  meta: { fontSize: 12, color: colors.muted, marginTop: 4, marginBottom: 8 },
  chapterBlock: { borderTopWidth: 1, borderTopColor: colors.grid },
  chapterRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12 },
  chapterNumber: {
    fontFamily: mono,
    fontSize: 12,
    color: colors.inkSoft,
    backgroundColor: colors.canvas,
    borderWidth: 1,
    borderColor: colors.grid,
    paddingHorizontal: 7,
    paddingVertical: 3,
    marginRight: 10,
  },
  chapterTitle: { flex: 1, fontSize: 15, fontWeight: '600', color: colors.ink },
  caret: { fontFamily: mono, fontSize: 16, color: colors.muted, paddingHorizontal: 6 },
  body: { paddingLeft: 34, paddingBottom: 12 },
  actionRow: { flexDirection: 'row', marginBottom: 10 },
  action: { color: colors.accent, fontWeight: '600', fontSize: 14, marginRight: 20 },
  actionStrong: { color: colors.amber, fontWeight: '700', fontSize: 14 },
  moduleRow: { flexDirection: 'row', paddingVertical: 9, borderTopWidth: 1, borderTopColor: colors.grid },
  moduleNumber: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 42, marginTop: 2 },
  moduleTitle: { fontSize: 14, color: colors.ink, lineHeight: 20 },
  moduleQuiz: { fontSize: 13, color: colors.accent, marginTop: 4 },
});
