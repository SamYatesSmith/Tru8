import AsyncStorage from '@react-native-async-storage/async-storage';
import { createCheck } from './api';

interface QueuedCheck {
  id: string;
  data: {
    inputType: string;
    content?: string;
    url?: string;
    file?: any;
  };
  timestamp: number;
  retryCount: number;
}

const QUEUE_KEY = 'offline_check_queue';
const MAX_RETRIES = 3;

class OfflineQueueManager {
  private static instance: OfflineQueueManager;
  private processing = false;

  public static getInstance(): OfflineQueueManager {
    if (!OfflineQueueManager.instance) {
      OfflineQueueManager.instance = new OfflineQueueManager();
    }
    return OfflineQueueManager.instance;
  }

  async addToQueue(data: QueuedCheck['data']): Promise<string> {
    const queuedCheck: QueuedCheck = {
      id: `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      data,
      timestamp: Date.now(),
      retryCount: 0,
    };

    try {
      const queue = await this.getQueue();
      queue.push(queuedCheck);
      await this.saveQueue(queue);
      
      console.log(`Added check to offline queue: ${queuedCheck.id}`);
      return queuedCheck.id;
    } catch (error) {
      console.error('Failed to add to offline queue:', error);
      throw error;
    }
  }

  async processQueue(token: string): Promise<void> {
    if (this.processing) return;
    this.processing = true;

    try {
      const queue = await this.getQueue();
      if (queue.length === 0) {
        this.processing = false;
        return;
      }

      console.log(`Processing ${queue.length} queued checks...`);
      const processedIds: string[] = [];
      const failedChecks: QueuedCheck[] = [];

      for (const queuedCheck of queue) {
        try {
          console.log(`Processing offline check: ${queuedCheck.id}`);
          await createCheck(queuedCheck.data, token);
          processedIds.push(queuedCheck.id);
          console.log(`Successfully processed: ${queuedCheck.id}`);
        } catch (error: any) {
          console.error(`Failed to process ${queuedCheck.id}:`, error);
          
          queuedCheck.retryCount++;
          if (queuedCheck.retryCount < MAX_RETRIES) {
            failedChecks.push(queuedCheck);
          } else {
            console.log(`Max retries exceeded for ${queuedCheck.id}, removing from queue`);
          }
        }
      }

      // Update queue with only failed checks that haven't exceeded max retries
      await this.saveQueue(failedChecks);
      
      if (processedIds.length > 0) {
        console.log(`Successfully processed ${processedIds.length} offline checks`);
      }
      
      if (failedChecks.length > 0) {
        console.log(`${failedChecks.length} checks remain in offline queue`);
      }
    } catch (error) {
      console.error('Error processing offline queue:', error);
    } finally {
      this.processing = false;
    }
  }

  async getQueue(): Promise<QueuedCheck[]> {
    try {
      const stored = await AsyncStorage.getItem(QUEUE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to load offline queue:', error);
      return [];
    }
  }

  async getQueueCount(): Promise<number> {
    const queue = await this.getQueue();
    return queue.length;
  }

  async clearQueue(): Promise<void> {
    try {
      await AsyncStorage.removeItem(QUEUE_KEY);
      console.log('Offline queue cleared');
    } catch (error) {
      console.error('Failed to clear offline queue:', error);
    }
  }

  private async saveQueue(queue: QueuedCheck[]): Promise<void> {
    try {
      await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
      throw error;
    }
  }

  async removeFromQueue(id: string): Promise<void> {
    try {
      const queue = await this.getQueue();
      const filtered = queue.filter(item => item.id !== id);
      await this.saveQueue(filtered);
      console.log(`Removed ${id} from offline queue`);
    } catch (error) {
      console.error('Failed to remove from offline queue:', error);
    }
  }
}

export default OfflineQueueManager.getInstance();