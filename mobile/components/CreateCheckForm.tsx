import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '@clerk/clerk-expo';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { Link2, Type, Upload, Video, Loader2 } from 'lucide-react-native';
import { createCheck } from '@/lib/api';

type InputType = 'url' | 'text' | 'image' | 'video';

interface CreateCheckFormProps {
  onSuccess?: (checkId: string) => void;
}

export function CreateCheckForm({ onSuccess }: CreateCheckFormProps) {
  const [inputType, setInputType] = useState<InputType>('url');
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  
  const { getToken } = useAuth();

  const handleSubmit = async () => {
    if (loading) return;
    
    setLoading(true);
    
    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');

      const data: {
        inputType: InputType;
        content?: string;
        url?: string;
        file?: any;
      } = { inputType };

      switch (inputType) {
        case 'url':
        case 'video':
          if (!url.trim()) {
            Alert.alert('Error', 'Please enter a URL');
            return;
          }
          data.url = url.trim();
          break;
        
        case 'text':
          if (!text.trim()) {
            Alert.alert('Error', 'Please enter some text');
            return;
          }
          data.content = text.trim();
          break;
          
        case 'image':
          if (!file) {
            Alert.alert('Error', 'Please select an image');
            return;
          }
          data.file = file;
          break;
      }

      const result = await createCheck(data, token);
      
      Alert.alert(
        'Check Created',
        'Your fact-check is being processed...',
        [{ text: 'OK', onPress: () => onSuccess?.(result.check.id) }]
      );
      
      // Reset form
      setUrl('');
      setText('');
      setFile(null);
      
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create check');
    } finally {
      setLoading(false);
    }
  };

  const handleImagePicker = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera roll permission is required');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.8,
      exif: false,
    });

    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      
      // Check file size (6MB limit)
      if (asset.fileSize && asset.fileSize > 6 * 1024 * 1024) {
        Alert.alert('File too large', 'Please select an image smaller than 6MB');
        return;
      }
      
      setFile({
        uri: asset.uri,
        type: 'image/jpeg',
        name: 'image.jpg',
      });
    }
  };

  const inputTypeOptions = [
    { value: 'url' as const, label: 'Link/URL', icon: Link2 },
    { value: 'text' as const, label: 'Text', icon: Type },
    { value: 'image' as const, label: 'Image', icon: Upload },
    { value: 'video' as const, label: 'Video', icon: Video },
  ];

  return (
    <View className="p-6 space-y-6">
      {/* Title */}
      <Text className="text-2xl font-bold text-lightGrey">
        What would you like to fact-check?
      </Text>

      {/* Input Type Selector */}
      <View className="grid grid-cols-2 gap-3">
        {inputTypeOptions.map(({ value, label, icon: Icon }) => (
          <TouchableOpacity
            key={value}
            onPress={() => setInputType(value)}
            className={`p-4 rounded-lg border-2 items-center ${
              inputType === value
                ? 'border-lightGrey bg-lightGrey/10'
                : 'border-coolGrey'
            }`}
          >
            <Icon 
              size={24} 
              color={inputType === value ? '#ECECEC' : '#AAABB8'} 
            />
            <Text 
              className={`mt-2 text-sm font-medium ${
                inputType === value ? 'text-lightGrey' : 'text-coolGrey'
              }`}
            >
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Input Fields */}
      <View className="space-y-4">
        {(inputType === 'url' || inputType === 'video') && (
          <View>
            <Text className="text-lightGrey mb-2 font-medium">
              {inputType === 'url' ? 'URL or Link' : 'Video URL'}
            </Text>
            <TextInput
              value={url}
              onChangeText={setUrl}
              placeholder={
                inputType === 'url' 
                  ? 'https://example.com/article'
                  : 'https://youtube.com/watch?v=...'
              }
              placeholderTextColor="#AAABB8"
              className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg"
              keyboardType="url"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text className="text-coolGrey text-sm mt-1">
              {inputType === 'url' 
                ? 'Paste a link to an article, social media post, or webpage'
                : 'YouTube or Vimeo links supported (max 8 minutes)'
              }
            </Text>
          </View>
        )}

        {inputType === 'text' && (
          <View>
            <Text className="text-lightGrey mb-2 font-medium">Text Content</Text>
            <TextInput
              value={text}
              onChangeText={setText}
              placeholder="Paste or type the content you want to fact-check..."
              placeholderTextColor="#AAABB8"
              className="bg-deepPurpleGrey text-lightGrey p-4 rounded-lg min-h-[120px]"
              multiline
              textAlignVertical="top"
              maxLength={2500}
            />
            <Text className="text-coolGrey text-sm mt-1">
              Maximum 2,500 words. {text.split(' ').filter(Boolean).length} words entered.
            </Text>
          </View>
        )}

        {inputType === 'image' && (
          <View>
            <Text className="text-lightGrey mb-2 font-medium">Select Image</Text>
            <TouchableOpacity
              onPress={handleImagePicker}
              className="bg-deepPurpleGrey border-2 border-dashed border-coolGrey rounded-lg p-8 items-center"
            >
              <Upload size={32} color="#AAABB8" />
              <Text className="text-coolGrey mt-2 text-center">
                {file ? 'Image selected' : 'Tap to select image'}
              </Text>
              {file && (
                <Text className="text-lightGrey text-sm mt-1">
                  Ready to upload
                </Text>
              )}
            </TouchableOpacity>
            <Text className="text-coolGrey text-sm mt-1">
              Upload a screenshot or image containing text (max 6MB)
            </Text>
          </View>
        )}
      </View>

      {/* Submit Button */}
      <TouchableOpacity
        onPress={handleSubmit}
        disabled={loading}
        className="bg-lightGrey py-4 rounded-lg disabled:opacity-50"
      >
        <View className="flex-row items-center justify-center">
          {loading && (
            <Loader2 size={20} color="#2C2C54" className="mr-2 animate-spin" />
          )}
          <Text className="text-darkIndigo text-center font-semibold text-lg">
            {loading ? 'Creating Check...' : 'Start Fact-Check'}
          </Text>
        </View>
      </TouchableOpacity>
    </View>
  );
}