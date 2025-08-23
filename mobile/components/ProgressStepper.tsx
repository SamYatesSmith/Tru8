import { View, Text } from 'react-native';
import { CheckCircle, Clock, Circle } from 'lucide-react-native';

type PipelineStage = 'ingest' | 'extract' | 'retrieve' | 'verify' | 'judge' | 'complete';

interface ProgressStepperProps {
  currentStage: PipelineStage;
  progress: number; // 0-100
  message?: string;
  error?: string;
}

const stages = [
  { 
    key: 'ingest' as const, 
    label: 'Ingesting', 
    description: 'Processing your content...' 
  },
  { 
    key: 'extract' as const, 
    label: 'Extracting', 
    description: 'Finding claims to fact-check...' 
  },
  { 
    key: 'retrieve' as const, 
    label: 'Researching', 
    description: 'Gathering evidence from sources...' 
  },
  { 
    key: 'verify' as const, 
    label: 'Verifying', 
    description: 'Checking claims against evidence...' 
  },
  { 
    key: 'judge' as const, 
    label: 'Analyzing', 
    description: 'Generating verdict and rationale...' 
  },
];

function getStageIndex(stage: PipelineStage): number {
  if (stage === 'complete') return stages.length;
  return stages.findIndex(s => s.key === stage);
}

export function ProgressStepper({ 
  currentStage, 
  progress, 
  message, 
  error 
}: ProgressStepperProps) {
  const currentIndex = getStageIndex(currentStage);
  const isComplete = currentStage === 'complete';

  return (
    <View className="p-6 space-y-6">
      {/* Overall Progress */}
      <View className="space-y-2">
        <View className="flex-row justify-between">
          <Text className="text-lightGrey font-medium">
            {error ? 'Processing failed' : isComplete ? 'Complete!' : 'Processing...'}
          </Text>
          <Text className="text-coolGrey">{progress}%</Text>
        </View>
        
        {/* Progress Bar */}
        <View className="h-3 bg-deepPurpleGrey rounded-full overflow-hidden">
          <View 
            className="h-full bg-lightGrey transition-all"
            style={{ width: `${progress}%` }}
          />
        </View>
        
        {message && (
          <Text className="text-coolGrey text-sm">{message}</Text>
        )}
        {error && (
          <Text className="text-contradicted text-sm">{error}</Text>
        )}
      </View>

      {/* Stage Steps */}
      <View className="space-y-4">
        {stages.map((stage, index) => {
          const isCompleted = index < currentIndex;
          const isCurrent = index === currentIndex && !isComplete;
          const isPending = index > currentIndex;

          return (
            <View
              key={stage.key}
              className={`flex-row items-start gap-3 p-3 rounded-lg border-2 ${
                isCurrent
                  ? 'bg-lightGrey/10 border-lightGrey'
                  : isCompleted
                  ? 'bg-deepPurpleGrey/50 border-coolGrey'
                  : 'border-coolGrey/30'
              }`}
            >
              <View className="mt-0.5">
                {isCompleted ? (
                  <CheckCircle size={20} color="#ECECEC" />
                ) : isCurrent ? (
                  <Clock size={20} color="#ECECEC" />
                ) : (
                  <Circle size={20} color="#AAABB8" />
                )}
              </View>
              
              <View className="flex-1">
                <Text className={`font-medium ${
                  isCurrent 
                    ? 'text-lightGrey' 
                    : isCompleted 
                    ? 'text-lightGrey' 
                    : 'text-coolGrey'
                }`}>
                  {stage.label}
                </Text>
                <Text className="text-coolGrey text-sm mt-1">
                  {stage.description}
                </Text>
              </View>
            </View>
          );
        })}

        {/* Completion Step */}
        {isComplete && (
          <View className="flex-row items-start gap-3 p-3 rounded-lg border-2 bg-lightGrey/10 border-lightGrey">
            <CheckCircle size={20} color="#ECECEC" className="mt-0.5" />
            <View>
              <Text className="font-medium text-lightGrey">Complete!</Text>
              <Text className="text-coolGrey text-sm mt-1">
                Your fact-check results are ready.
              </Text>
            </View>
          </View>
        )}
      </View>
    </View>
  );
}