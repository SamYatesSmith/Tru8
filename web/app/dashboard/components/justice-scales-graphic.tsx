import Image from 'next/image';

export function JusticeScalesGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/truthscales.png"
        alt="Justice scales"
        fill
        sizes="256px"
        loading="eager"
        className="object-contain"
      />
    </div>
  );
}
