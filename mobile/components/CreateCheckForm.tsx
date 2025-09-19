import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, Alert } from 'react-native';
import { useAuth } from '@clerk/clerk-expo';
// import * as DocumentPicker from 'expo-document-picker'; // TODO: implement file upload
import * as ImagePicker from 'expo-image-picker';
import { Link2, Type, Upload, Video, Loader2, Camera, Image as ImageIcon, WifiOff } from 'lucide-react-native';
import { createCheck } from '@/lib/api';
import { Colors, Spacing, Typography, BorderRadius } from '@/lib/design-system';
import { useNetwork } from '@/hooks/use-network';
import OfflineQueueManager from '@/lib/offline-queue';

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
  const { isOnline } = useNetwork();

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

      // Check if offline and queue the request
      if (!isOnline) {
        const queuedId = await OfflineQueueManager.addToQueue(data);
        
        Alert.alert(
          'Added to Queue',
          'You\'re offline. Your fact-check has been queued and will be processed when you\'re back online.',
          [{ text: 'OK', onPress: () => onSuccess?.(queuedId) }]
        );
        
        // Reset form
        setUrl('');
        setText('');
        setFile(null);
        return;
      }

      // Try to process offline queue first if online
      if (isOnline) {
        try {
          await OfflineQueueManager.processQueue(token);
        } catch (queueError) {
          console.log('Queue processing failed, but continuing with current request:', queueError);
        }
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
      console.error('Create check error:', error);
      
      // Network error while online - add to offline queue
      if (error.name === 'NetworkError' || error.code === 'NETWORK_ERROR' || !isOnline) {
        try {
          const queuedId = await OfflineQueueManager.addToQueue({
            inputType,
            content: inputType === 'text' ? text.trim() : undefined,
            url: (inputType === 'url' || inputType === 'video') ? url.trim() : undefined,
            file: inputType === 'image' ? file : undefined,
          });
          
          Alert.alert(
            'Added to Queue',
            'Network error occurred. Your fact-check has been queued and will be processed when connection is restored.',
            [{ text: 'OK', onPress: () => onSuccess?.(queuedId) }]
          );
          
          // Reset form
          setUrl('');
          setText('');
          setFile(null);
          return;
        } catch (queueError) {
          console.error('Failed to add to queue:', queueError);
        }
      }
      
      let errorMessage = 'Failed to create check';
      
      if (error.status === 402) {
        errorMessage = 'Insufficient credits. Please upgrade your plan to continue.';
      } else if (error.status === 413) {
        errorMessage = 'File too large. Please select a smaller image.';
      } else if (error.status === 400) {
        errorMessage = error.message || 'Invalid input. Please check your data and try again.';
      } else if (error.status >= 500) {
        errorMessage = 'Server error. Please try again in a moment.';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      Alert.alert(
        'Error',
        errorMessage,
        [
          { text: 'OK' },
          ...(error.status >= 500 ? [{
            text: 'Retry',
            onPress: () => handleSubmit()
          }] : [])
        ]
      );
    } finally {
      setLoading(false);
    }
  };

  // Removed showImagePicker - using direct camera/library buttons instead

  const handleCamera = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera permission is required');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.8,
      exif: false,
    });

    if (!result.canceled && result.assets[0]) {
      processImageAsset(result.assets[0]);
    }
  };

  const handleImageLibrary = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Photo library permission is required');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.8,
      exif: false,
    });

    if (!result.canceled && result.assets[0]) {
      processImageAsset(result.assets[0]);
    }
  };

  const processImageAsset = (asset: ImagePicker.ImagePickerAsset) => {
    // Check file size (6MB limit)
    if (asset.fileSize && asset.fileSize > 6 * 1024 * 1024) {
      Alert.alert('File too large', 'Please select an image smaller than 6MB');
      return;
    }
    
    setFile({
      uri: asset.uri,
      type: asset.type || 'image/jpeg',
      name: asset.fileName || `image_${Date.now()}.jpg`,
      size: asset.fileSize,
    });
  };

  const inputTypeOptions = [
    { value: 'url' as const, label: 'Link/URL', icon: Link2 },
    { value: 'text' as const, label: 'Text', icon: Type },
    { value: 'image' as const, label: 'Image', icon: Upload },
    { value: 'video' as const, label: 'Video', icon: Video },
  ];

  return (
    <View style={{ padding: Spacing.space6, gap: Spacing.space6 }}>
      {/* Offline Status */}
      {!isOnline && (
        <View style={{
          backgroundColor: Colors.verdictContradicted + '20',
          borderColor: Colors.verdictContradicted,
          borderWidth: 1,
          borderRadius: BorderRadius.radiusLg,
          padding: Spacing.space3,
          flexDirection: 'row',
          alignItems: 'center',
          gap: Spacing.space2,
        }}>
          <WifiOff size={20} color={Colors.verdictContradicted} />
          <Text style={{
            color: Colors.verdictContradicted,
            fontSize: Typography.textSm,
            fontWeight: Typography.fontWeightMedium,
            flex: 1,
          }}>
            You're offline. Checks will be queued and processed when connection is restored.
          </Text>
        </View>
      )}

      {/* Title */}
      <Text style={{
        fontSize: Typography.text2xl,
        fontWeight: Typography.fontWeightBold,
        color: Colors.lightGrey,
        textAlign: 'center',
      }}>
        What would you like to fact-check?
      </Text>

      {/* Input Type Selector */}
      <View style={{ 
        flexDirection: 'row', 
        flexWrap: 'wrap', 
        gap: Spacing.space3,
        justifyContent: 'space-between',
      }}>
        {inputTypeOptions.map(({ value, label, icon: Icon }) => (
          <TouchableOpacity
            key={value}
            onPress={() => setInputType(value)}
            style={{
              padding: Spacing.space4,
              borderRadius: BorderRadius.radiusLg,
              borderWidth: 2,
              borderColor: inputType === value ? Colors.lightGrey : Colors.coolGrey,
              backgroundColor: inputType === value 
                ? `${Colors.lightGrey}1A` // 10% opacity
                : 'transparent',
              alignItems: 'center',
              width: '47%', // Two columns with gap
            }}
          >
            <Icon 
              size={24} 
              color={inputType === value ? Colors.lightGrey : Colors.coolGrey} 
            />
            <Text 
              style={{
                marginTop: Spacing.space2,
                fontSize: Typography.textSm,
                fontWeight: Typography.fontWeightMedium,
                color: inputType === value ? Colors.lightGrey : Colors.coolGrey,
              }}
            >
              {label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Input Fields */}
      <View style={{ gap: Spacing.space4 }}>
        {(inputType === 'url' || inputType === 'video') && (
          <View>
            <Text style={{
              color: Colors.lightGrey,
              marginBottom: Spacing.space2,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>
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
              placeholderTextColor={Colors.coolGrey}
              style={{
                backgroundColor: Colors.deepPurpleGrey,
                color: Colors.lightGrey,
                padding: Spacing.space4,
                borderRadius: BorderRadius.radiusLg,
                fontSize: Typography.textBase,
              }}
              keyboardType="url"
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textSm,
              marginTop: Spacing.space1,
            }}>
              {inputType === 'url' 
                ? 'Paste a link to an article, social media post, or webpage'
                : 'YouTube or Vimeo links supported (max 8 minutes)'
              }
            </Text>
          </View>
        )}

        {inputType === 'text' && (
          <View>
            <Text style={{
              color: Colors.lightGrey,
              marginBottom: Spacing.space2,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>Text Content</Text>
            <TextInput
              value={text}
              onChangeText={setText}
              placeholder="Paste or type the content you want to fact-check..."
              placeholderTextColor={Colors.coolGrey}
              style={{
                backgroundColor: Colors.deepPurpleGrey,
                color: Colors.lightGrey,
                padding: Spacing.space4,
                borderRadius: BorderRadius.radiusLg,
                minHeight: 120,
                fontSize: Typography.textBase,
              }}
              multiline
              textAlignVertical="top"
              maxLength={2500}
            />
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textSm,
              marginTop: Spacing.space1,
            }}>
              Maximum 2,500 words. {text.split(' ').filter(Boolean).length} words entered.
            </Text>
          </View>
        )}

        {inputType === 'image' && (
          <View>
            <Text style={{
              color: Colors.lightGrey,
              marginBottom: Spacing.space2,
              fontSize: Typography.textBase,
              fontWeight: Typography.fontWeightMedium,
            }}>Select Image</Text>
            {!file ? (
              <View style={{ gap: Spacing.space3 }}>
                {/* Camera Option */}
                <TouchableOpacity
                  onPress={handleCamera}
                  style={{
                    backgroundColor: Colors.deepPurpleGrey,
                    borderWidth: 2,
                    borderColor: Colors.coolGrey,
                    borderRadius: BorderRadius.radiusLg,
                    padding: Spacing.space4,
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: Spacing.space3,
                  }}
                >
                  <Camera size={24} color={Colors.lightGrey} />
                  <Text style={{
                    color: Colors.lightGrey,
                    fontSize: Typography.textBase,
                    fontWeight: Typography.fontWeightMedium,
                  }}>
                    Take Photo
                  </Text>
                </TouchableOpacity>

                {/* Gallery Option */}
                <TouchableOpacity
                  onPress={handleImageLibrary}
                  style={{
                    backgroundColor: Colors.deepPurpleGrey,
                    borderWidth: 2,
                    borderColor: Colors.coolGrey,
                    borderRadius: BorderRadius.radiusLg,
                    padding: Spacing.space4,
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: Spacing.space3,
                  }}
                >
                  <ImageIcon size={24} color={Colors.lightGrey} />
                  <Text style={{
                    color: Colors.lightGrey,
                    fontSize: Typography.textBase,
                    fontWeight: Typography.fontWeightMedium,
                  }}>
                    Choose from Gallery
                  </Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={{
                backgroundColor: Colors.deepPurpleGrey,
                borderRadius: BorderRadius.radiusLg,
                padding: Spacing.space4,
                alignItems: 'center',
                gap: Spacing.space2,
              }}>
                <Upload size={32} color={Colors.verdictSupported} />
                <Text style={{
                  color: Colors.lightGrey,
                  fontSize: Typography.textBase,
                  fontWeight: Typography.fontWeightMedium,
                }}>
                  Image Selected
                </Text>
                <Text style={{
                  color: Colors.coolGrey,
                  fontSize: Typography.textSm,
                  textAlign: 'center',
                }}>
                  {file.name}
                </Text>
                <TouchableOpacity
                  onPress={() => setFile(null)}
                  style={{
                    marginTop: Spacing.space2,
                    paddingVertical: Spacing.space1,
                    paddingHorizontal: Spacing.space3,
                    borderRadius: BorderRadius.radiusMd,
                    borderWidth: 1,
                    borderColor: Colors.coolGrey,
                  }}
                >
                  <Text style={{
                    color: Colors.coolGrey,
                    fontSize: Typography.textSm,
                  }}>
                    Change
                  </Text>
                </TouchableOpacity>
              </View>
            )}
            <Text style={{
              color: Colors.coolGrey,
              fontSize: Typography.textSm,
              marginTop: Spacing.space1,
            }}>
              Upload a screenshot or image containing text (max 6MB)
            </Text>
          </View>
        )}
      </View>

      {/* Submit Button */}
      <TouchableOpacity
        onPress={handleSubmit}
        disabled={loading}
        style={{
          backgroundColor: loading ? `${Colors.lightGrey}80` : Colors.lightGrey, // 50% opacity when disabled
          paddingVertical: Spacing.space4,
          borderRadius: BorderRadius.radiusLg,
        }}
      >
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {loading && (
            <Loader2 size={20} color={Colors.darkIndigo} style={{ marginRight: Spacing.space2 }} />
          )}
          <Text style={{
            color: Colors.darkIndigo,
            textAlign: 'center',
            fontSize: Typography.textLg,
            fontWeight: Typography.fontWeightSemibold,
          }}>
            {loading ? 'Creating Check...' : 'Start Fact-Check'}
          </Text>
        </View>
      </TouchableOpacity>
    </View>
  );
}