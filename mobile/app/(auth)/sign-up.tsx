import { useSignUp } from '@clerk/clerk-expo';
import { Link, router } from 'expo-router';
import { Text, TextInput, TouchableOpacity, View } from 'react-native';
import { useState } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '@/lib/design-system';

export default function SignUp() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const [emailAddress, setEmailAddress] = useState('');
  const [password, setPassword] = useState('');
  const [pendingVerification, setPendingVerification] = useState(false);
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const onSignUpPress = async () => {
    if (!isLoaded) return;
    setLoading(true);

    try {
      await signUp.create({
        emailAddress,
        password,
      });

      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
      setPendingVerification(true);
    } catch (err: any) {
      console.log(JSON.stringify(err, null, 2));
    } finally {
      setLoading(false);
    }
  };

  const onPressVerify = async () => {
    if (!isLoaded) return;
    setLoading(true);

    try {
      const completeSignUp = await signUp.attemptEmailAddressVerification({
        code,
      });

      if (completeSignUp.status === 'complete') {
        await setActive({ session: completeSignUp.createdSessionId });
        router.replace('/');
      } else {
        console.log(JSON.stringify(completeSignUp, null, 2));
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
            {pendingVerification 
              ? "We've sent a verification code to your email"
              : "Join the fight against misinformation"}
          </Text>
        </View>

        {!pendingVerification ? (
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
                keyboardType="email-address"
              />
            </View>

            <View>
              <Text className="text-lightGrey mb-2 font-medium">Password</Text>
              <TextInput
                value={password}
                placeholder="Create a secure password..."
                placeholderTextColor={Colors.coolGrey}
                secureTextEntry={true}
                onChangeText={setPassword}
                className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg"
              />
              <Text className="text-coolGrey text-sm mt-1">
                Must be at least 8 characters
              </Text>
            </View>

            <TouchableOpacity
              onPress={onSignUpPress}
              disabled={loading}
              className="bg-lightGrey py-4 rounded-lg mt-6 disabled:opacity-50"
            >
              <Text className="text-darkIndigo text-center font-semibold text-lg">
                {loading ? 'Creating Account...' : 'Sign Up'}
              </Text>
            </TouchableOpacity>

            <View className="flex-row justify-center mt-6">
              <Text className="text-coolGrey">Already have an account? </Text>
              <Link href="/(auth)/sign-in" asChild>
                <TouchableOpacity>
                  <Text className="text-lightGrey font-medium">Sign in</Text>
                </TouchableOpacity>
              </Link>
            </View>
          </View>
        ) : (
          <View className="space-y-4">
            <View>
              <Text className="text-lightGrey mb-2 font-medium">Verification Code</Text>
              <TextInput
                value={code}
                placeholder="Enter the 6-digit code..."
                placeholderTextColor={Colors.coolGrey}
                onChangeText={setCode}
                className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg text-center text-2xl"
                keyboardType="number-pad"
                maxLength={6}
              />
            </View>

            <TouchableOpacity
              onPress={onPressVerify}
              disabled={loading}
              className="bg-lightGrey py-4 rounded-lg mt-6 disabled:opacity-50"
            >
              <Text className="text-darkIndigo text-center font-semibold text-lg">
                {loading ? 'Verifying...' : 'Verify Email'}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              onPress={() => setPendingVerification(false)}
              className="mt-4"
            >
              <Text className="text-coolGrey text-center">
                Back to sign up
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </SafeAreaView>
  );
}