import Image from 'next/image';

export function JusticeScalesGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/truthscales.png"
        alt="Justice scales"
        fill
        className="object-contain"
      />
    </div>
  );
}
