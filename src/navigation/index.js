import {
  DrawerContentScrollView,
  DrawerItemList,
  createDrawerNavigator,
} from '@react-navigation/drawer';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { ConfirmDialog, Loading } from '../components/ui';
import AccessProvision from '../screens/faculty/AccessProvision';
import { AdminAnalytics, AdminCourses, AdminDashboard, AdminReview, AdminUsers }
  from '../screens/admin/AdminScreens';
import FacultyCourseDetail from '../screens/faculty/FacultyCourseDetail';
import { ChapterWorkshop, ProgressScreen, RubricsScreen }
  from '../screens/faculty/TeachingScreens';
import FacultyCourses from '../screens/faculty/FacultyCourses';
import FacultyDashboard from '../screens/faculty/FacultyDashboard';
import QuizPreview from '../screens/faculty/QuizPreview';
import { LoginScreen, RegisterScreen } from '../screens/shared/AuthScreens';
import ContentScreen from '../screens/shared/ContentScreen';
import ProfileScreen from '../screens/shared/ProfileScreen';
import CoursesProvided from '../screens/student/CoursesProvided';
import FeedbackScreen from '../screens/student/FeedbackScreen';
import QuizScreen from '../screens/student/QuizScreen';
import ResultScreen from '../screens/student/ResultScreen';
import StudentCourseDetail from '../screens/student/StudentCourseDetail';
import StudentCourses from '../screens/student/StudentCourses';
import StudentDashboard from '../screens/student/StudentDashboard';
import { useAuth } from '../store/auth';
import { colors, radius, spacing } from '../theme';

const Drawer = createDrawerNavigator();
const Stack = createNativeStackNavigator();

const stackOptions = {
  headerStyle: { backgroundColor: colors.paper },
  headerTintColor: colors.ink,
  headerTitleStyle: { fontWeight: '700', color: colors.ink },
  headerShadowVisible: false,
  contentStyle: { backgroundColor: colors.canvas },
};

function FacultyCourseStack() {
  return (
    <Stack.Navigator screenOptions={stackOptions}>
      <Stack.Screen name="FacultyCourses" component={FacultyCourses} options={{ headerShown: false }} />
      <Stack.Screen name="FacultyCourseDetail" component={FacultyCourseDetail} />
      <Stack.Screen name="Content" component={ContentScreen} />
      <Stack.Screen name="QuizPreview" component={QuizPreview} />
      <Stack.Screen name="ChapterWorkshop" component={ChapterWorkshop} />
    </Stack.Navigator>
  );
}

function StudentCourseStack() {
  return (
    <Stack.Navigator screenOptions={stackOptions}>
      <Stack.Screen name="StudentCourses" component={StudentCourses} options={{ headerShown: false }} />
      <Stack.Screen name="StudentCourseDetail" component={StudentCourseDetail} />
      <Stack.Screen name="Content" component={ContentScreen} />
      <Stack.Screen name="Quiz" component={QuizScreen} />
      <Stack.Screen name="Result" component={ResultScreen} options={{ headerBackVisible: false }} />
    </Stack.Navigator>
  );
}

function Sidebar(props) {
  const { user, signOut } = useAuth();
  const [confirming, setConfirming] = React.useState(false);
  return (
    <DrawerContentScrollView
      {...props}
      style={styles.drawerBody}
      contentContainerStyle={styles.drawerContent}
    >
      <View style={styles.brand}>
        <View style={styles.mark}>
          <Text style={styles.markText}>X</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.brandName} numberOfLines={1}>MIS 3000</Text>
          <Text style={styles.brandRole}>
            {user?.role === 'ADMIN'
              ? 'Admin'
              : user?.role === 'FACULTY'
              ? 'Faculty'
              : 'Student'}
          </Text>
        </View>
      </View>

      <View style={styles.items}>
        <DrawerItemList {...props} />
      </View>

      <View style={styles.account}>
        <Text style={styles.accountName} numberOfLines={1}>{user?.name}</Text>
        <Text style={styles.accountEmail} numberOfLines={1}>{user?.email}</Text>
        <Pressable onPress={() => setConfirming(true)}>
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
        <ConfirmDialog
          visible={confirming}
          title="Sign out?"
          message="You will need your email and password to get back in."
          confirmLabel="Yes, sign out"
          cancelLabel="No, stay"
          onCancel={() => setConfirming(false)}
          onConfirm={() => {
            setConfirming(false);
            signOut();
          }}
        />
      </View>
    </DrawerContentScrollView>
  );
}

// On a wide screen the sidebar stays open beside the content, the way the design shows it.
// On a phone it slides in from the left behind a menu button, since there is no room for both.
const WIDE = 900;

const drawerOptions = {
  headerStyle: { backgroundColor: colors.paper },
  headerTintColor: colors.ink,
  headerTitleStyle: { fontWeight: '700', color: colors.ink },
  headerShadowVisible: false,
  drawerActiveBackgroundColor: colors.accent,
  drawerActiveTintColor: colors.paper,
  drawerInactiveTintColor: colors.sidebarText,
  drawerLabelStyle: { fontSize: 15, fontWeight: '600', marginLeft: -12 },
  drawerItemStyle: { borderRadius: radius.control, paddingLeft: 4, marginVertical: 2 },
  drawerStyle: { backgroundColor: colors.sidebar, width: 258 },
  sceneContainerStyle: { backgroundColor: colors.canvas },
};

// A plain glyph rather than an icon package, so the sidebar reads like the design
// without pulling another dependency into the project.
function icon(glyph) {
  return ({ color }) => <Text style={[styles.itemIcon, { color }]}>{glyph}</Text>;
}

function useLayoutOptions() {
  const { width } = useWindowDimensions();
  const wide = width >= WIDE;
  return {
    ...drawerOptions,
    drawerType: wide ? 'permanent' : 'front',
    headerShown: !wide,
    overlayColor: wide ? 'transparent' : 'rgba(11,31,23,0.4)',
  };
}

function FacultyApp() {
  const screenOptions = useLayoutOptions();
  return (
    <Drawer.Navigator drawerContent={(props) => <Sidebar {...props} />} screenOptions={screenOptions}>
      <Drawer.Screen name="Dashboard" component={FacultyDashboard} options={{ drawerIcon: icon('▦') }} />
      <Drawer.Screen name="Course" component={FacultyCourseStack} options={{ drawerIcon: icon('▤') }} />
      <Drawer.Screen name="Access provision" component={AccessProvision} options={{ drawerIcon: icon('✉') }} />
      <Drawer.Screen name="Rubrics" component={RubricsScreen} options={{ drawerIcon: icon('✎') }} />
      <Drawer.Screen name="Progress" component={ProgressScreen} options={{ drawerIcon: icon('◔') }} />
      <Drawer.Screen name="Profile" component={ProfileScreen} options={{ drawerIcon: icon('○') }} />
    </Drawer.Navigator>
  );
}

function StudentApp() {
  const screenOptions = useLayoutOptions();
  return (
    <Drawer.Navigator drawerContent={(props) => <Sidebar {...props} />} screenOptions={screenOptions}>
      <Drawer.Screen name="Dashboard" component={StudentDashboard} options={{ drawerIcon: icon('▦') }} />
      <Drawer.Screen name="Courses provided" component={CoursesProvided} options={{ drawerIcon: icon('✉') }} />
      <Drawer.Screen name="Course" component={StudentCourseStack} options={{ drawerIcon: icon('▤') }} />
      <Drawer.Screen name="Feedback" component={FeedbackScreen} options={{ drawerIcon: icon('◔') }} />
      <Drawer.Screen name="Profile" component={ProfileScreen} options={{ drawerIcon: icon('○') }} />
    </Drawer.Navigator>
  );
}

function AdminApp() {
  const screenOptions = useLayoutOptions();
  return (
    <Drawer.Navigator drawerContent={(props) => <Sidebar {...props} />} screenOptions={screenOptions}>
      <Drawer.Screen name="Dashboard" component={AdminDashboard} options={{ drawerIcon: icon('▦') }} />
      <Drawer.Screen name="Users" component={AdminUsers} options={{ drawerIcon: icon('✦') }} />
      <Drawer.Screen name="Courses" component={AdminCourses} options={{ drawerIcon: icon('▤') }} />
      <Drawer.Screen name="Review" component={AdminReview} options={{ drawerIcon: icon('✎') }} />
      <Drawer.Screen name="Analytics" component={AdminAnalytics} options={{ drawerIcon: icon('◔') }} />
      <Drawer.Screen name="Profile" component={ProfileScreen} options={{ drawerIcon: icon('○') }} />
    </Drawer.Navigator>
  );
}

function AuthApp() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Register" component={RegisterScreen} />
    </Stack.Navigator>
  );
}

export default function Navigation() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Starting up" />;
  return (
    <NavigationContainer>
      {!user ? (
        <AuthApp />
      ) : user.role === 'ADMIN' ? (
        <AdminApp />
      ) : user.role === 'FACULTY' ? (
        <FacultyApp />
      ) : (
        <StudentApp />
      )}
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  drawerBody: { backgroundColor: colors.sidebar },
  itemIcon: { fontSize: 15, width: 20, textAlign: 'center' },
  drawerContent: { paddingTop: 0, flexGrow: 1 },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing(2),
    paddingTop: spacing(2.5),
    paddingBottom: spacing(2),
  },
  mark: {
    width: 34,
    height: 34,
    borderRadius: 8,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  markText: { color: colors.paper, fontSize: 17, fontWeight: '700' },
  brandName: { color: colors.paper, fontSize: 17, fontWeight: '700' },
  brandRole: { color: colors.sidebarText, fontSize: 12.5, marginTop: 1 },
  items: { paddingHorizontal: 8, paddingTop: spacing(0.5), flexGrow: 1 },
  account: {
    marginTop: spacing(3),
    marginHorizontal: spacing(2),
    borderTopWidth: 1,
    borderTopColor: colors.sidebarLine,
    paddingTop: spacing(2),
    paddingBottom: spacing(2),
  },
  accountName: { color: colors.paper, fontSize: 14.5, fontWeight: '700' },
  accountEmail: { color: colors.sidebarText, fontSize: 12.5, marginTop: 2 },
  signOutText: {
    color: colors.sidebarText,
    fontSize: 13.5,
    marginTop: 10,
    textDecorationLine: 'underline',
  },
});
