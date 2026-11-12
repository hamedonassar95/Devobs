import React, { useState, useRef } from 'react';
import {
  Video,
  Image as ImageIcon,
  Music,
  Sparkles,
  Play,
  Pause,
  Download,
  Upload,
  RefreshCw,
  Film,
  Sliders,
  Layers,
  Wand2,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Volume2,
} from 'lucide-react';

export function AiMediaStudio() {
  const [activeSubTab, setActiveSubTab] = useState<'video' | 'image' | 'music'>('video');

  // Video State
  const [videoPrompt, setVideoPrompt] = useState(
    'A cinematic 3D pan across a high-security cyber server room with pulsating blue and emerald LED blade servers and cooling steam vents.'
  );
  const [videoAspectRatio, setVideoAspectRatio] = useState<'16:9' | '9:16'>('16:9');
  const [videoImageSource, setVideoImageSource] = useState<string | null>(null);
  const [isVideoLoading, setIsVideoLoading] = useState(false);
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState<string | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);

  // Image State
  const [imagePrompt, setImagePrompt] = useState(
    'A high-tech isometric 3D server rack cluster with holographic network topology floating above, cyber neon lighting'
  );
  const [sourceImageForEdit, setSourceImageForEdit] = useState<string | null>(null);
  const [isImageLoading, setIsImageLoading] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);

  // Music State
  const [musicPrompt, setMusicPrompt] = useState(
    'Futuristic electronic ambient synthwave soundtrack for a cyber DevOps command center, deep bass rhythm and digital chimes'
  );
  const [isFullTrack, setIsFullTrack] = useState(false);
  const [isMusicLoading, setIsMusicLoading] = useState(false);
  const [generatedMusicUrl, setGeneratedMusicUrl] = useState<string | null>(null);
  const [musicLyrics, setMusicLyrics] = useState<string | null>(null);
  const [musicError, setMusicError] = useState<string | null>(null);
  const [isPlayingMusic, setIsPlayingMusic] = useState(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Video file upload
  const handleVideoImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setVideoImageSource(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Image file upload for editing
  const handleImageEditUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSourceImageForEdit(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Generate Video with gemini-omni-1.2-flash
  const handleGenerateVideo = async () => {
    setIsVideoLoading(true);
    setVideoError(null);
    setGeneratedVideoUrl(null);

    try {
      let imageBase64: string | undefined;
      let mimeType: string | undefined;

      if (videoImageSource) {
        const parts = videoImageSource.split(',');
        mimeType = parts[0].match(/:(.*?);/)?.[1] || 'image/png';
        imageBase64 = parts[1];
      }

      const res = await fetch('/api/ai/generate-video', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: videoPrompt,
          imageBase64,
          mimeType,
          aspectRatio: videoAspectRatio,
        }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'فشل في توليد الفيديو');
      }

      if (data.videoBase64) {
        setGeneratedVideoUrl(`data:${data.mimeType || 'video/mp4'};base64,${data.videoBase64}`);
      }
    } catch (err: any) {
      console.error('Video error:', err);
      setVideoError(err.message || 'حدث خطأ أثناء طلب توليد الفيديو');
    } finally {
      setIsVideoLoading(false);
    }
  };

  // Generate or Edit Image with gemini-nano-banana-2.1
  const handleGenerateImage = async () => {
    setIsImageLoading(true);
    setImageError(null);
    setGeneratedImageUrl(null);

    try {
      let imageBase64: string | undefined;
      let mimeType: string | undefined;

      if (sourceImageForEdit) {
        const parts = sourceImageForEdit.split(',');
        mimeType = parts[0].match(/:(.*?);/)?.[1] || 'image/png';
        imageBase64 = parts[1];
      }

      const res = await fetch('/api/ai/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: imagePrompt,
          imageBase64,
          mimeType,
          aspectRatio: '1:1',
        }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'فشل في توليد الصورة');
      }

      if (data.imageBase64) {
        setGeneratedImageUrl(`data:${data.mimeType || 'image/png'};base64,${data.imageBase64}`);
      }
    } catch (err: any) {
      console.error('Image error:', err);
      setImageError(err.message || 'حدث خطأ أثناء توليد أو تعديل الصورة');
    } finally {
      setIsImageLoading(false);
    }
  };

  // Generate Music with Lyria (lyria-3-clip-preview / lyria-3-pro-preview)
  const handleGenerateMusic = async () => {
    setIsMusicLoading(true);
    setMusicError(null);
    setGeneratedMusicUrl(null);
    setMusicLyrics(null);

    try {
      const res = await fetch('/api/ai/generate-music', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: musicPrompt,
          fullTrack: isFullTrack,
        }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'فشل في توليد المقطع الصوتي');
      }

      if (data.audioBase64) {
        setGeneratedMusicUrl(`data:${data.mimeType || 'audio/wav'};base64,${data.audioBase64}`);
        if (data.lyrics) setMusicLyrics(data.lyrics);
      }
    } catch (err: any) {
      console.error('Music error:', err);
      setMusicError(err.message || 'حدث خطأ أثناء توليد الموسيقى');
    } finally {
      setIsMusicLoading(false);
    }
  };

  const toggleMusicPlayback = () => {
    if (!audioPlayerRef.current) return;
    if (isPlayingMusic) {
      audioPlayerRef.current.pause();
      setIsPlayingMusic(false);
    } else {
      audioPlayerRef.current.play();
      setIsPlayingMusic(true);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Navigation tabs */}
      <div className="border-b border-slate-800 bg-slate-950/80 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            استوديو وسائط الذكاء الاصطناعي (AI Media Studio)
          </h3>
          <p className="text-xs text-slate-400">
            توليد الفيديو، الرسوم التوضيحية، وتوليد نغمات ومقاطع التنبيهات باستخدام أحدث نماذج Gemini و Lyria
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setActiveSubTab('video')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeSubTab === 'video'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            توليد الفيديو (Omni Flash)
          </button>

          <button
            onClick={() => setActiveSubTab('image')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeSubTab === 'image'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            توليد وتعديل الصور (Nano Banana 2.1)
          </button>

          <button
            onClick={() => setActiveSubTab('music')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
              activeSubTab === 'music'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Music className="w-3.5 h-3.5" />
            توليد النغمات والموسيقى (Lyria)
          </button>
        </div>
      </div>

      <div className="p-6">
        {/* --- 1. Video Studio Tab --- */}
        {activeSubTab === 'video' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-3">
                <label className="block text-xs font-semibold text-slate-300">
                  وصف مشهد الفيديو المراد توليده أو تحريكه:
                </label>
                <textarea
                  rows={3}
                  value={videoPrompt}
                  onChange={(e) => setVideoPrompt(e.target.value)}
                  placeholder="اكتب وصفاً دقيقاً لحركة الكاميرا والإضاءة وعناصر الخوادم..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />

                {/* Aspect ratio */}
                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-slate-400">نسبة العرض إلى الارتفاع:</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setVideoAspectRatio('16:9')}
                      className={`px-3 py-1 rounded-lg border font-mono ${
                        videoAspectRatio === '16:9'
                          ? 'bg-indigo-600/30 text-indigo-400 border-indigo-500'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      16:9 (أفقي سينمائي)
                    </button>
                    <button
                      type="button"
                      onClick={() => setVideoAspectRatio('9:16')}
                      className={`px-3 py-1 rounded-lg border font-mono ${
                        videoAspectRatio === '9:16'
                          ? 'bg-indigo-600/30 text-indigo-400 border-indigo-500'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      9:16 (عمودي للهواتف)
                    </button>
                  </div>
                </div>

                {/* Optional Image Upload for Image-to-Video Animation */}
                <div className="pt-2 border-t border-slate-800">
                  <label className="block text-xs text-slate-400 mb-2">
                    تحريك صورة ثابتة إلى فيديو (اختياري - Animate Image):
                  </label>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-2 transition-colors">
                      <Upload className="w-3.5 h-3.5" />
                      اختر صورة من جهازك
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleVideoImageUpload}
                        className="hidden"
                      />
                    </label>
                    {videoImageSource && (
                      <div className="flex items-center gap-2">
                        <img
                          src={videoImageSource}
                          alt="Source preview"
                          className="w-8 h-8 rounded object-cover border border-slate-700"
                        />
                        <button
                          type="button"
                          onClick={() => setVideoImageSource(null)}
                          className="text-rose-400 text-xs hover:underline"
                        >
                          إلغاء
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Generate Button */}
                <button
                  type="button"
                  onClick={handleGenerateVideo}
                  disabled={isVideoLoading || !videoPrompt.trim()}
                  className="w-full mt-2 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition-all"
                >
                  {isVideoLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      جاري معالجة الفيديو بواسطة gemini-omni-1.2-flash...
                    </>
                  ) : (
                    <>
                      <Film className="w-4 h-4" />
                      {videoImageSource ? 'تحريك الصورة إلى فيديو' : 'توليد الفيديو بالذكاء الاصطناعي'}
                    </>
                  )}
                </button>
              </div>

              {videoError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {videoError}
                </div>
              )}
            </div>

            {/* Video Preview Area */}
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-4 flex flex-col items-center justify-center min-h-[320px]">
              {isVideoLoading ? (
                <div className="text-center space-y-3">
                  <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
                  <p className="text-sm font-semibold text-white">
                    جاري التوليد البصري والتحريك الزمني...
                  </p>
                  <p className="text-xs text-slate-500">
                    توليد الفيديو يستغرق بضع ثوانٍ لحساب الإطارات بمعدل 720p
                  </p>
                </div>
              ) : generatedVideoUrl ? (
                <div className="w-full space-y-3">
                  <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-black">
                    <video
                      src={generatedVideoUrl}
                      controls
                      autoPlay
                      loop
                      className="w-full h-auto max-h-[380px] mx-auto object-contain"
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      تم إنشاء الفيديو بنجاح ({videoAspectRatio})
                    </span>
                    <a
                      href={generatedVideoUrl}
                      download={`serverops-video-${Date.now()}.mp4`}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 shadow"
                    >
                      <Download className="w-3 h-3" />
                      تنزيل الفيديو
                    </a>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-2 text-slate-500">
                  <Film className="w-12 h-12 mx-auto stroke-[1.2] text-slate-600" />
                  <p className="text-sm">لم يتم توليد أي فيديو بعد</p>
                  <p className="text-xs">
                    اكتب نصاً أو ارفع صورة، ثم انقر على "توليد الفيديو" لإنشاء مقطع مرئي بدقة عالية
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* --- 2. Image Studio Tab --- */}
        {activeSubTab === 'image' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-3">
                <label className="block text-xs font-semibold text-slate-300">
                  وصف الصورة أو التعديل المطلوب (gemini-nano-banana-2.1):
                </label>
                <textarea
                  rows={3}
                  value={imagePrompt}
                  onChange={(e) => setImagePrompt(e.target.value)}
                  placeholder="اكتب وصفاً لصورة البنية التحتية، خوادم السحابة، أو الشارات الهندسية..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />

                {/* Optional Image Upload for Editing */}
                <div className="pt-2 border-t border-slate-800">
                  <label className="block text-xs text-slate-400 mb-2">
                    تعديل صورة حالية (اختياري - Image Editing):
                  </label>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs text-slate-300 flex items-center gap-2 transition-colors">
                      <Upload className="w-3.5 h-3.5" />
                      رفع صورة للتعديل
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageEditUpload}
                        className="hidden"
                      />
                    </label>
                    {sourceImageForEdit && (
                      <div className="flex items-center gap-2">
                        <img
                          src={sourceImageForEdit}
                          alt="Source preview"
                          className="w-8 h-8 rounded object-cover border border-slate-700"
                        />
                        <button
                          type="button"
                          onClick={() => setSourceImageForEdit(null)}
                          className="text-rose-400 text-xs hover:underline"
                        >
                          إلغاء
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGenerateImage}
                  disabled={isImageLoading || !imagePrompt.trim()}
                  className="w-full mt-2 py-3 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-cyan-600/30 transition-all"
                >
                  {isImageLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      جاري إنشاء الصورة بواسطة gemini-nano-banana-2.1...
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      {sourceImageForEdit ? 'تعديل الصورة الذكي' : 'توليد الصورة بدقة 1K'}
                    </>
                  )}
                </button>
              </div>

              {imageError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {imageError}
                </div>
              )}
            </div>

            {/* Image Preview Area */}
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-4 flex flex-col items-center justify-center min-h-[320px]">
              {isImageLoading ? (
                <div className="text-center space-y-3">
                  <Loader2 className="w-10 h-10 animate-spin text-cyan-400 mx-auto" />
                  <p className="text-sm font-semibold text-white">جاري الرسم والتوليد البصري...</p>
                </div>
              ) : generatedImageUrl ? (
                <div className="w-full space-y-3 text-center">
                  <img
                    src={generatedImageUrl}
                    alt="Generated by Gemini"
                    className="max-h-[340px] rounded-lg mx-auto object-contain border border-slate-700 shadow-xl"
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      تم إنشاء الصورة
                    </span>
                    <a
                      href={generatedImageUrl}
                      download={`serverops-image-${Date.now()}.png`}
                      className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium flex items-center gap-1.5 shadow"
                    >
                      <Download className="w-3 h-3" />
                      تنزيل الصورة
                    </a>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-2 text-slate-500">
                  <ImageIcon className="w-12 h-12 mx-auto stroke-[1.2] text-slate-600" />
                  <p className="text-sm">لم يتم توليد أي صورة بعد</p>
                  <p className="text-xs">
                    استخدم النموذج لإنشاء مخططات بصرية للبنية التحتية، أو أيقونات مخصصة
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* --- 3. Music Studio Tab (Lyria) --- */}
        {activeSubTab === 'music' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-3">
                <label className="block text-xs font-semibold text-slate-300">
                  وصف النغمة أو المقطع الصوتي المراد إنتاجه (Lyria):
                </label>
                <textarea
                  rows={3}
                  value={musicPrompt}
                  onChange={(e) => setMusicPrompt(e.target.value)}
                  placeholder="نغمة إنذار طوارئ إلكترونية، أو مقطع هادئ لغرفة العمليات..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />

                {/* Track length option */}
                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-slate-400">نوع المقطع:</span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setIsFullTrack(false)}
                      className={`px-3 py-1 rounded-lg border font-mono ${
                        !isFullTrack
                          ? 'bg-purple-600/30 text-purple-400 border-purple-500'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      مقطع قصير (Lyria Clip 30s)
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsFullTrack(true)}
                      className={`px-3 py-1 rounded-lg border font-mono ${
                        isFullTrack
                          ? 'bg-purple-600/30 text-purple-400 border-purple-500'
                          : 'bg-slate-900 text-slate-400 border-slate-800'
                      }`}
                    >
                      مسار كامل (Lyria Pro)
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGenerateMusic}
                  disabled={isMusicLoading || !musicPrompt.trim()}
                  className="w-full mt-2 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:opacity-50 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-purple-600/30 transition-all"
                >
                  {isMusicLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      جاري إنتاج المقطع الموسيقي بواسطة Lyria...
                    </>
                  ) : (
                    <>
                      <Music className="w-4 h-4" />
                      توليد المقطع الصوتي
                    </>
                  )}
                </button>
              </div>

              {musicError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {musicError}
                </div>
              )}
            </div>

            {/* Music Player & Preview */}
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-6 flex flex-col items-center justify-center min-h-[320px]">
              {isMusicLoading ? (
                <div className="text-center space-y-3">
                  <Loader2 className="w-10 h-10 animate-spin text-purple-400 mx-auto" />
                  <p className="text-sm font-semibold text-white">جاري توليد النغمات وتوليف الصوت...</p>
                </div>
              ) : generatedMusicUrl ? (
                <div className="w-full space-y-5 text-center">
                  <audio
                    ref={audioPlayerRef}
                    src={generatedMusicUrl}
                    onEnded={() => setIsPlayingMusic(false)}
                    className="hidden"
                  />

                  <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-purple-600 to-pink-600 flex items-center justify-center mx-auto shadow-xl shadow-purple-600/30 text-white">
                    <button
                      type="button"
                      onClick={toggleMusicPlayback}
                      className="w-full h-full flex items-center justify-center hover:scale-105 transition-transform"
                    >
                      {isPlayingMusic ? (
                        <Pause className="w-8 h-8 fill-current" />
                      ) : (
                        <Play className="w-8 h-8 fill-current translate-x-0.5" />
                      )}
                    </button>
                  </div>

                  <div>
                    <h4 className="text-base font-bold text-white">مقطع صوتي مُولد بواسطة Lyria</h4>
                    <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto line-clamp-2">
                      {musicPrompt}
                    </p>
                  </div>

                  {musicLyrics && (
                    <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs text-slate-300 max-w-sm mx-auto text-right">
                      <span className="text-[10px] text-purple-400 font-semibold block mb-1">
                        الكلمات / الوصف المصاحب:
                      </span>
                      {musicLyrics}
                    </div>
                  )}

                  <div className="flex items-center justify-center gap-3 pt-2">
                    <a
                      href={generatedMusicUrl}
                      download={`serverops-audio-${Date.now()}.wav`}
                      className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow"
                    >
                      <Download className="w-3.5 h-3.5" />
                      تنزيل المقطع الصوتي (WAV)
                    </a>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-2 text-slate-500">
                  <Volume2 className="w-12 h-12 mx-auto stroke-[1.2] text-slate-600" />
                  <p className="text-sm">لم يتم توليد أي صوت بعد</p>
                  <p className="text-xs">
                    أنشئ مؤثرات صوتية لغرف العمليات، أو نغمات تنبيهات فورية للأعطال الحرجة
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
