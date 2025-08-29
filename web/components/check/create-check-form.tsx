"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Upload, Link, Type, Video } from "lucide-react";
import { createCheck } from "@/lib/api";
import type { InputType } from "@shared/types";

interface CreateCheckFormProps {
  onSuccess?: (checkId: string) => void;
}

export function CreateCheckForm({ onSuccess }: CreateCheckFormProps) {
  const [inputType, setInputType] = useState<InputType>("url");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  
  const { getToken } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const createCheckMutation = useMutation({
    mutationFn: async (data: { inputType: InputType; content?: string; url?: string; file?: File }) => {
      const token = await getToken();
      return createCheck(data, token);
    },
    onSuccess: (data) => {
      toast({
        title: "Check created",
        description: "Your fact-check is being processed...",
      });
      queryClient.invalidateQueries({ queryKey: ["checks"] });
      queryClient.invalidateQueries({ queryKey: ["user"] });
      onSuccess?.(data.check.id);
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to create check",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const data: { inputType: InputType; content?: string; url?: string; file?: File } = {
      inputType,
    };

    switch (inputType) {
      case "url":
        if (!url.trim()) {
          toast({
            title: "Error",
            description: "Please enter a URL",
            variant: "destructive",
          });
          return;
        }
        data.url = url.trim();
        break;
      
      case "text":
        if (!text.trim()) {
          toast({
            title: "Error", 
            description: "Please enter some text",
            variant: "destructive",
          });
          return;
        }
        data.content = text.trim();
        break;
        
      case "image":
      case "video":
        if (!file) {
          toast({
            title: "Error",
            description: `Please select a ${inputType}`,
            variant: "destructive",
          });
          return;
        }
        data.file = file;
        break;
    }

    createCheckMutation.mutate(data);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file size (6MB limit)
      const maxSize = 6 * 1024 * 1024; // 6MB
      if (selectedFile.size > maxSize) {
        toast({
          title: "File too large",
          description: "Please select a file smaller than 6MB",
          variant: "destructive",
        });
        return;
      }
      setFile(selectedFile);
    }
  };

  const inputTypeOptions = [
    { value: "url", label: "Link/URL", icon: Link },
    { value: "text", label: "Text", icon: Type },
    { value: "image", label: "Image", icon: Upload },
    { value: "video", label: "Video", icon: Video },
  ] as const;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Input Type Selector */}
      <div>
        <Label className="text-base font-semibold">What would you like to fact-check?</Label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          {inputTypeOptions.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              type="button"
              onClick={() => setInputType(value)}
              className={`p-4 rounded-lg border-2 transition-all hover:bg-accent ${
                inputType === value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border"
              }`}
            >
              <Icon className="h-6 w-6 mx-auto mb-2" />
              <div className="text-sm font-medium">{label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Input Fields */}
      <div className="space-y-4">
        {inputType === "url" && (
          <div>
            <Label htmlFor="url">URL or Link</Label>
            <Input
              id="url"
              type="url"
              placeholder="https://example.com/article"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              Paste a link to an article, social media post, or webpage
            </p>
          </div>
        )}

        {inputType === "text" && (
          <div>
            <Label htmlFor="text">Text Content</Label>
            <Textarea
              id="text"
              placeholder="Paste or type the content you want to fact-check..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              required
              maxLength={2500} // From project limits
            />
            <p className="text-sm text-muted-foreground mt-1">
              Maximum 2,500 words. {text.split(' ').length} words entered.
            </p>
          </div>
        )}

        {inputType === "image" && (
          <div>
            <Label htmlFor="image">Upload Image</Label>
            <Input
              id="image"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              required
            />
            {file && (
              <p className="text-sm text-muted-foreground mt-1">
                Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
            <p className="text-sm text-muted-foreground mt-1">
              Upload a screenshot or image containing text (max 6MB)
            </p>
          </div>
        )}

        {inputType === "video" && (
          <div>
            <Label htmlFor="video">Video URL</Label>
            <Input
              id="video"
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <p className="text-sm text-muted-foreground mt-1">
              YouTube or Vimeo links supported (max 8 minutes)
            </p>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <Button 
        type="submit" 
        className="w-full" 
        size="lg"
        disabled={createCheckMutation.isPending}
      >
        {createCheckMutation.isPending ? "Creating Check..." : "Start Fact-Check"}
      </Button>
    </form>
  );
}