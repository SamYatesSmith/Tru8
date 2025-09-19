import { useSignIn } from '@clerk/clerk-expo';
import { Link, router } from 'expo-router';
import { Text, TextInput, TouchableOpacity, View } from 'react-native';
import { useState } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '@/lib/design-system';

export default function SignIn() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const [emailAddress, setEmailAddress] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const onSignInPress = async () => {
    if (!isLoaded) {
      return;
    }
    setLoading(true);

    try {
      const signInAttempt = await signIn.create({
        identifier: emailAddress,
        password,
      });

      if (signInAttempt.status === 'complete') {
        await setActive({ session: signInAttempt.createdSessionId });
        router.replace('/');
      } else {
        console.log(JSON.stringify(signInAttempt, null, 2));
      }
    } catch (err: any) {
      console.log(JSON.stringify(err, null, 2));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-darkIndigo">
      <View className="flex-1 justify-center px-8">
        <View className="mb-12 items-center">
          <Text className="text-4xl font-bold text-lightGrey mb-2">Tru8</Text>
          <Text className="text-coolGrey text-center">
            Instant fact-checking with dated evidence
          </Text>
        </View>

        <View className="space-y-4">
          <View>
            <Text className="text-lightGrey mb-2 font-medium">Email</Text>
            <TextInput
              autoCapitalize="none"
              value={emailAddress}
              placeholder="Enter your email..."
              placeholderTextColor={Colors.coolGrey}
              onChangeText={setEmailAddress}
              className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg"
            />
          </View>

          <View>
            <Text className="text-lightGrey mb-2 font-medium">Password</Text>
            <TextInput
              value={password}
              placeholder="Enter your password..."
              placeholderTextColor={Colors.coolGrey}
              secureTextEntry={true}
              onChangeText={setPassword}
              className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg"
            />
          </View>

          <TouchableOpacity
            onPress={onSignInPress}
            disabled={loading}
            className="bg-lightGrey py-4 rounded-lg mt-6 disabled:opacity-50"
          >
            <Text className="text-darkIndigo text-center font-semibold text-lg">
              {loading ? 'Signing in...' : 'Sign In'}
            </Text>
          </TouchableOpacity>

          <View className="flex-row justify-center mt-6">
            <Text className="text-coolGrey">Don't have an account? </Text>
            <Link href="/(auth)/sign-up" asChild>
              <TouchableOpacity>
                <Text className="text-lightGrey font-medium">Sign up</Text>
              </TouchableOpacity>
            </Link>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}