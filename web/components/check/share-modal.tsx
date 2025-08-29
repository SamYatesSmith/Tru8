"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { 
  Copy, 
  Twitter, 
  Linkedin, 
  Facebook, 
  Mail, 
  Share2,
  Check,
  QrCode
} from "lucide-react";
import { cn } from "@/lib/utils";
import QRCode from "qrcode";
import { useEffect, useState as useQRState } from "react";

interface ShareModalProps {
  checkId: string;
  title?: string;
  verdict?: string;
  children?: React.ReactNode;
}

export function ShareModal({ checkId, title, verdict, children }: ShareModalProps) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);
  const [qrCode, setQrCode] = useQRState<string>("");
  const [showQR, setShowQR] = useState(false);
  
  const shareUrl = typeof window !== 'undefined' 
    ? `${window.location.origin}/checks/${checkId}`
    : '';

  const shareTitle = title || "Fact-check results from Tru8";
  const shareText = verdict 
    ? `This claim is ${verdict}. Check the full analysis:`
    : "View the detailed fact-check analysis:";

  useEffect(() => {
    if (showQR && shareUrl) {
      QRCode.toDataURL(shareUrl, {
        width: 256,
        margin: 2,
        color: {
          dark: '#1E40AF',
          light: '#FFFFFF'
        }
      }).then(setQrCode);
    }
  }, [showQR, shareUrl]);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast({
        title: "Link copied!",
        description: "The share link has been copied to your clipboard.",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast({
        title: "Failed to copy",
        description: "Please try selecting and copying the link manually.",
        variant: "destructive",
      });
    }
  };

  const shareVia = (platform: string) => {
    const encodedUrl = encodeURIComponent(shareUrl);
    const encodedText = encodeURIComponent(shareText);
    const encodedTitle = encodeURIComponent(shareTitle);
    
    const urls: Record<string, string> = {
      twitter: `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      email: `mailto:?subject=${encodedTitle}&body=${encodedText}%20${encodedUrl}`,
    };
    
    if (urls[platform]) {
      window.open(urls[platform], '_blank', 'width=600,height=400');
    }
  };

  const shareNative = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: shareTitle,
          text: shareText,
          url: shareUrl,
        });
      } catch (err) {
        // User cancelled or error
        console.log('Share cancelled');
      }
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        {children || (
          <Button variant="outline">
            <Share2 className="h-4 w-4 mr-2" />
            Share Results
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Fact-Check Results</DialogTitle>
          <DialogDescription>
            Share this fact-check with others via social media or direct link.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* URL Copy Section */}
          <div className="space-y-2">
            <Label htmlFor="share-link">Share Link</Label>
            <div className="flex gap-2">
              <Input
                id="share-link"
                value={shareUrl}
                readOnly
                className="flex-1"
              />
              <Button
                size="icon"
                variant="outline"
                onClick={copyToClipboard}
                className="flex-shrink-0"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Social Share Buttons */}
          <div className="space-y-2">
            <Label>Share on Social Media</Label>
            <div className="grid grid-cols-4 gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => shareVia('twitter')}
                className="hover:bg-blue-50"
                title="Share on Twitter"
              >
                <Twitter className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => shareVia('linkedin')}
                className="hover:bg-blue-50"
                title="Share on LinkedIn"
              >
                <Linkedin className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => shareVia('facebook')}
                className="hover:bg-blue-50"
                title="Share on Facebook"
              >
                <Facebook className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => shareVia('email')}
                className="hover:bg-gray-50"
                title="Share via Email"
              >
                <Mail className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* QR Code Section */}
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => setShowQR(!showQR)}
            >
              <QrCode className="h-4 w-4 mr-2" />
              {showQR ? 'Hide' : 'Show'} QR Code
            </Button>
            
            {showQR && qrCode && (
              <div className="flex justify-center p-4 bg-gray-50 rounded-lg">
                <img src={qrCode} alt="QR Code" className="w-48 h-48" />
              </div>
            )}
          </div>

          {/* Native Share (if available) */}
          {typeof navigator !== 'undefined' && 'share' in navigator && (
            <Button
              variant="default"
              className="w-full btn-primary"
              onClick={shareNative}
            >
              <Share2 className="h-4 w-4 mr-2" />
              Share via System
            </Button>
          )}
        </div>

        <DialogFooter>
          <DialogTrigger asChild>
            <Button variant="outline">Close</Button>
          </DialogTrigger>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}