import Image from 'next/image';

export function PrismGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/prism.newcheck.png"
        alt="Prism"
        fill
        className="object-contain"
      />
    </div>
  );
}
