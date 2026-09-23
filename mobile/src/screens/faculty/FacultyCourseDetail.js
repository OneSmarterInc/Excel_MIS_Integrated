import { useFocusEffect } from '@react-navigation/native';
import * as DocumentPicker from 'expo-document-picker';
import React, { useCallback, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import api, { API_HOST, downloadDocument, readError } from '../../api/client';
import { Button, ConfirmDialog, Empty, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

const ACCEPTED = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'application/vnd.ms-powerpoint',
  'text/plain',
];

export default function FacultyCourseDetail({ route, navigation }) {
  const { id, code } = route.params;
  const [course, setCourse] = useState(null);
  const [students, setStudents] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [openChapter, setOpenChapter] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [downloading, setDownloading] = useState('');
  const [pendingRemoval, setPendingRemoval] = useState(null);

  const download = async (path, filename, label) => {
    setDownloading(filename);
    setMessage('');
    setError('');
    try {
      const result = await downloadDocument(path, filename);
      setMessage(
        result.saved
          ? `${label} saved as ${result.saved} (${result.characters.toLocaleString()} characters).`
          : `${label} came through, ${result.characters.toLocaleString()} characters. `
            + 'Install expo-file-system to save it on a phone, or use the browser.'
      );
    } catch (err) {
      setError(err.message || readError(err));
    } finally {
      setDownloading('');
    }
  };
  const [generating, setGenerating] = useState(false);
  const [panel, setPanel] = useState(route.params?.openPanel || null);
  const [topics, setTopics] = useState('');
  const [picked, setPicked] = useState([]);

  const load = useCallback(async () => {
    try {
      const [detail, roster, marks] = await Promise.all([
        api.get(`/courses/${id}/`),
        api.get(`/courses/${id}/students/`),
        api.get(`/courses/${id}/performance/`),
      ]);
      setCourse(detail.data);
      setStudents(roster.data);
      setPerformance(marks.data);
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

  const upload = async () => {
    setMessage('');
    setError('');
    const picked = await DocumentPicker.getDocumentAsync({ type: ACCEPTED, copyToCacheDirectory: true });
    if (picked.canceled || !picked.assets?.length) return;
    const file = picked.assets[0];

    const body = new FormData();
    body.append('title', file.name.replace(/\.[^.]+$/, ''));
    if (Platform.OS === 'web') {
      body.append('file', file.file, file.name);
    } else {
      body.append('file', {
        uri: file.uri,
        name: file.name,
        type: file.mimeType || 'application/octet-stream',
      });
    }

    setUploading(true);
    try {
      const { data } = await api.post(`/courses/${id}/books/`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setMessage(
        `${data.title} stored. ${data.chapter_count} chapters and ${data.module_count} modules were pulled out. ${data.extraction_note}`
      );
      load();
    } catch (err) {
      setError(readError(err, 'That file could not be read.'));
    } finally {
      setUploading(false);
    }
  };

  // The other way in: slides, a montage, screenshots or just a list of topic names.
  // Whatever text can be read from them becomes the outline, and the book is written
  // from there.
  const pickMaterial = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: [...ACCEPTED, 'image/*'],
      multiple: true,
      copyToCacheDirectory: true,
    });
    if (result.canceled || !result.assets?.length) return;
    setPicked((prev) => [...prev, ...result.assets]);
  };

  const generate = async () => {
    setMessage('');
    setError('');
    if (!picked.length && !topics.trim()) {
      setError('Add some slides or images, or type a few topic names.');
      return;
    }
    const body = new FormData();
    body.append('title', `${course.name} course book`);
    if (topics.trim()) body.append('topics', topics.trim());
    picked.forEach((file) => {
      if (Platform.OS === 'web') {
        body.append('files', file.file, file.name);
      } else {
        body.append('files', {
          uri: file.uri,
          name: file.name,
          type: file.mimeType || 'application/octet-stream',
        });
      }
    });

    setGenerating(true);
    try {
      const { data } = await api.post(`/courses/${id}/generate-book/`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 900000,
      });
      setMessage(
        `${data.title} written. ${data.chapter_count} chapters and ${data.module_count} modules are ready for students. ${data.extraction_note}`
      );
      setPicked([]);
      setTopics('');
      setPanel(null);
      load();
    } catch (err) {
      setError(readError(err, 'The book could not be written from those files.'));
    } finally {
      setGenerating(false);
    }
  };

  const removeBook = async (bookId) => {
    try {
      await api.delete(`/books/${bookId}/`);
      setMessage('Book removed with its chapters and modules.');
      load();
    } catch (err) {
      setError(readError(err));
    }
  };

  if (!course) return <Loading label="Loading course" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>{course.name}</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Course code {course.code}. Students join with it from their own login.
      </Text>

      <ConfirmDialog
        visible={!!pendingRemoval}
        title="Remove this book?"
        message={
          pendingRemoval
            ? `${pendingRemoval.title} and its ${pendingRemoval.chapter_count} chapters and `
              + `${pendingRemoval.module_count} modules go with it. This cannot be undone.`
            : ''
        }
        confirmLabel="Yes, remove it"
        cancelLabel="No, keep it"
        onCancel={() => setPendingRemoval(null)}
        onConfirm={() => {
          const book = pendingRemoval;
          setPendingRemoval(null);
          removeBook(book.id);
        }}
      />

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <View style={styles.pathRow}>
        <Button
          tone={panel === 'generate' ? 'quiet' : 'accent'}
          label={uploading ? 'Reading the file' : 'Upload a book'}
          onPress={upload}
          disabled={uploading || generating}
          style={{ flex: 1, marginRight: 8 }}
        />
        <Button
          tone={panel === 'generate' ? 'accent' : 'quiet'}
          label="Build from slides or topics"
          onPress={() => setPanel(panel === 'generate' ? null : 'generate')}
          disabled={uploading || generating}
          style={{ flex: 1 }}
        />
      </View>

      {panel === 'generate' ? (
        <Surface>
          <Text style={type.heading}>Build the book from what you have</Text>
          <Text style={[type.small, { marginTop: 6, marginBottom: spacing(1.5) }]}>
            Add your lecture slides, a montage, screenshots or a handout. Headings become the
            chapters and modules, and the text of each module is written from the material. An
            image carries no readable text, so name your files after the topic they cover, or
            type the topics below.
          </Text>

          <Button tone="quiet" label="Choose slides, images or documents" onPress={pickMaterial} />
          {picked.length ? (
            <View style={styles.pickedList}>
              {picked.map((file, index) => (
                <View key={`${file.name}-${index}`} style={styles.pickedRow}>
                  <Text style={styles.pickedName} numberOfLines={1}>{file.name}</Text>
                  <Pressable onPress={() => setPicked((prev) => prev.filter((_, i) => i !== index))}>
                    <Text style={styles.remove}>Remove</Text>
                  </Pressable>
                </View>
              ))}
            </View>
          ) : null}

          <View style={{ height: spacing(2) }} />
          <Text style={styles.topicsLabel}>Topic names, one per line (optional)</Text>
          <TextInput
            value={topics}
            onChangeText={setTopics}
            multiline
            placeholder={'Data flow diagrams\nEntity relationship diagrams\nUse cases'}
            placeholderTextColor={colors.muted}
            style={styles.topicsInput}
          />
          <Button
            tone="accent"
            label={generating ? 'Writing the book, this takes a few minutes' : 'Build the book'}
            onPress={generate}
            disabled={generating}
            style={{ marginTop: spacing(1.5) }}
          />
        </Surface>
      ) : null}

      {course.books.length === 0 ? (
        <Empty
          title="No book uploaded"
          body="Upload the textbook and the app will find the chapters, split each one into modules and keep the text it extracted."
        />
      ) : (
        course.books.map((book) => (
          <Surface key={book.id}>
            <View style={styles.bookHead}>
              <View style={{ flex: 1 }}>
                <Text style={styles.bookTitle}>{book.title}</Text>
                <Text style={styles.meta}>
                  {book.source === 'GENERATED' ? 'BUILT FOR YOU' : book.kind.toUpperCase()}  ·  {book.chapter_count} chapters  ·  {book.module_count} modules
                  {'  ·  '}
                  {book.character_count.toLocaleString()} characters
                </Text>
              </View>
              <Pressable onPress={() => setPendingRemoval(book)}>
                <Text style={styles.remove}>Remove</Text>
              </Pressable>
            </View>
            <Text style={styles.note}>{book.extraction_note}</Text>

            {book.chapters.map((chapter) => {
              const open = openChapter === chapter.id;
              return (
                <View key={chapter.id} style={styles.chapterBlock}>
                  <Pressable
                    onPress={() => setOpenChapter(open ? null : chapter.id)}
                    style={styles.chapterRow}
                  >
                    <Text style={styles.chapterNumber}>{chapter.number}</Text>
                    <Text style={styles.chapterTitle} numberOfLines={2}>{chapter.title}</Text>
                    <Text style={styles.chapterStatus}>{chapter.status}</Text>
                    <Text style={styles.caret}>{open ? '\u2013' : '+'}</Text>
                  </Pressable>

                  {open ? (
                    <View style={styles.chapterBody}>
                      <Pressable
                        onPress={() =>
                          navigation.navigate('Content', {
                            kind: 'chapter',
                            id: chapter.id,
                            title: chapter.title,
                          })
                        }
                      >
                        <Text style={styles.action}>Read the chapter explanation</Text>
                      </Pressable>
                      <Pressable
                        onPress={() => download(
                          `/chapters/${chapter.id}/download/`,
                          `${course.code}_chapter_${chapter.number}.pdf`,
                          `Chapter ${chapter.number}`
                        )}
                      >
                        <Text style={styles.action}>Download this chapter (PDF)</Text>
                      </Pressable>
                      <Pressable
                        onPress={() =>
                          navigation.navigate('ChapterWorkshop', {
                            id: chapter.id,
                            bookId: book.id,
                          })
                        }
                      >
                        <Text style={styles.action}>
                          Edit, add references and send for approval
                        </Text>
                      </Pressable>
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
                              <Text style={styles.moduleTitle} numberOfLines={2}>
                                {module.title}
                              </Text>
                            </Pressable>
                            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                              <Pressable
                                onPress={() =>
                                  navigation.navigate('QuizPreview', {
                                    kind: 'module',
                                    id: module.id,
                                    title: `Module ${chapter.number}.${module.number}: ${module.title}`,
                                  })
                                }
                              >
                                <Text style={styles.moduleSets}>
                                  Question sets for this module
                                </Text>
                              </Pressable>
                              <Pressable
                                onPress={() =>
                                  download(
                                    `/modules/${module.id}/download/`,
                                    `${course.code}_module_${chapter.number}_${module.number}.pdf`,
                                    `Module ${chapter.number}.${module.number}`
                                  )
                                }
                              >
                                <Text style={[styles.moduleSets, { color: colors.accent, fontWeight: '600' }]}>
                                  Download PDF
                                </Text>
                              </Pressable>
                            </View>
                          </View>
                        </View>
                      ))}
                    </View>
                  ) : null}
                </View>
              );
            })}

            <Button
              tone="quiet"
              label={
                downloading
                  ? 'Building PDF file...'
                  : `Download the whole book as PDF (${book.chapter_count} chapters, ${book.module_count} modules)`
              }
              disabled={!!downloading}
              onPress={() => download(
                `/books/${book.id}/download/`,
                `${course.code}_${book.id}_book.pdf`,
                'The whole book'
              )}
              style={{ marginTop: spacing(1.5) }}
            />
          </Surface>
        ))
      )}

      <Surface>
        <Text style={type.heading}>Enrolled students</Text>
        {students.length === 0 ? (
          <Text style={[type.small, { marginTop: 6 }]}>
            Nobody has joined with {course.code} yet.
          </Text>
        ) : (
          students.map((row) => (
            <View key={row.id} style={styles.studentRow}>
              <Text style={styles.studentName}>{row.student_name}</Text>
              <Text style={styles.meta}>{row.student_email}</Text>
            </View>
          ))
        )}
      </Surface>

      {performance && performance.students.length ? (
        <Surface>
          <Text style={type.heading}>Quiz results</Text>
          <Text style={[type.small, { marginBottom: 8 }]}>
            Class average {performance.average_percentage}% on {performance.marks} marks across{' '}
            {performance.attempts} {performance.attempts === 1 ? 'attempt' : 'attempts'}
          </Text>
          {performance.students.map((row) => (
            <View key={row.student_email} style={styles.markRow}>
              <Text style={styles.studentName}>{row.student_name}</Text>
              <Text style={styles.mark}>
                {row.score}/{row.total}  ({row.percentage}%)
              </Text>
            </View>
          ))}
        </Surface>
      ) : null}

      <Text style={styles.host}>Server: {API_HOST}</Text>
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
  bookHead: { flexDirection: 'row', alignItems: 'flex-start' },
  bookTitle: { fontSize: 16, fontWeight: '700', color: colors.ink },
  meta: { fontSize: 12, color: colors.muted, marginTop: 4 },
  remove: { color: colors.red, fontSize: 13, fontWeight: '600', paddingLeft: 10 },
  note: { fontSize: 12, color: colors.accent, marginTop: 6, marginBottom: 10 },
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
  chapterStatus: { fontSize: 11, color: colors.muted, paddingHorizontal: 8 },
  chapterBody: { paddingBottom: 12, paddingLeft: 34 },
  action: { color: colors.accent, fontWeight: '600', fontSize: 14, marginBottom: 10 },
  moduleRow: { flexDirection: 'row', paddingVertical: 8, alignItems: 'flex-start' },
  moduleNumber: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 40, marginTop: 2 },
  moduleTitle: { fontSize: 14, color: colors.ink, lineHeight: 20 },
  moduleSets: { fontSize: 12.5, color: colors.accent, marginTop: 3 },
  studentRow: { paddingVertical: 8, borderTopWidth: 1, borderTopColor: colors.grid, marginTop: 8 },
  studentName: { fontSize: 15, color: colors.ink, fontWeight: '600' },
  markRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
  },
  mark: { fontFamily: mono, fontSize: 13, color: colors.inkSoft },
  host: { fontFamily: mono, fontSize: 11, color: colors.muted, marginTop: spacing(1) },
  pathRow: { flexDirection: 'row', marginBottom: spacing(2) },
  pickedList: { marginTop: spacing(1.5) },
  pickedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    paddingVertical: 8,
  },
  pickedName: { flex: 1, fontFamily: mono, fontSize: 12, color: colors.ink, paddingRight: 8 },
  topicsLabel: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  topicsInput: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    minHeight: 90,
    padding: 10,
    fontSize: 14,
    color: colors.ink,
    textAlignVertical: 'top',
  },
});
